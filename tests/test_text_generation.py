"""Generation checks use mock CLI/HTTP calls; no models or desktop apps start."""
import json
import subprocess
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError
from utils import text_generation as generation

PARAGRAPH = ("A curious clockmaker visited a quiet village and repaired a forgotten bell. " * 6)[:400]


class GenerationTests(unittest.TestCase):
    def test_explicit_load_without_ttl_or_unload(self):
        replies = ["", "", "[]", json.dumps([{"modelKey": "gpt-oss-20b", "path": "model.gguf"}]), ""]
        with patch.object(generation, "find_lms", return_value="lms"), patch.object(generation, "run_lms", side_effect=replies) as run:
            self.assertEqual(generation.ensure_model(lambda _: None), generation.MODEL_IDENTIFIER)
        calls = [call.args for call in run.call_args_list]
        self.assertEqual(calls[0], ("lms", "daemon", "up"))
        self.assertIn(("lms", "server", "start", "--port", "1234", "--bind", "127.0.0.1"), calls)
        load = calls[-1]
        self.assertEqual(load[:3], ("lms", "load", "gpt-oss-20b"))
        self.assertNotIn("--ttl", load)
        self.assertFalse(any("unload" in call for call in calls))

    def test_reuses_loaded_model_without_loading_a_second_copy(self):
        replies = ["", "", json.dumps([{"identifier": "existing", "path": "model.gguf"}]),
                   json.dumps([{"modelKey": "gpt-oss-20b", "path": "model.gguf"}])]
        with patch.object(generation, "find_lms", return_value="lms"), patch.object(generation, "run_lms", side_effect=replies) as run:
            self.assertEqual(generation.ensure_model(lambda _: None), "existing")
            self.assertFalse(any("load" in call.args for call in run.call_args_list))

    def test_missing_model_does_not_fall_back_or_download(self):
        with patch.object(generation, "find_lms", return_value="lms"), patch.object(generation, "run_lms", side_effect=["", "", "[]", "[]"]) as run:
            with self.assertRaisesRegex(generation.GenerationError, "not downloaded"):
                generation.ensure_model(lambda _: None)
            self.assertEqual(run.call_count, 4)

    def test_fresh_stateless_prompts_languages_and_length_revisions(self):
        reply = lambda text: {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]}
        with patch.object(generation, "ensure_model", return_value="model"), patch.object(generation, "request_json", side_effect=[reply("Too short."), reply(PARAGRAPH), reply(PARAGRAPH)]) as request:
            self.assertEqual(generation.generate_passage("German"), PARAGRAPH)
            self.assertEqual(generation.generate_passage("English"), PARAGRAPH)
            self.assertIn("German", request.call_args_list[0].args[1]["messages"][1]["content"])
            self.assertIn("English", request.call_args_list[-1].args[1]["messages"][1]["content"])
            for call in request.call_args_list:
                messages = call.args[1]["messages"]
                self.assertEqual([message["role"] for message in messages], ["system", "user"])
                self.assertNotIn(PARAGRAPH, str(messages))

    def test_never_uses_reasoning_as_passage_or_clips_long_text(self):
        self.assertEqual(generation.clean_passage("<think>private analysis</think> Hello\nworld."), "Hello world.")
        with self.assertRaises(generation.GenerationError):
            generation.clean_passage("<think>unfinished")
        reply = {"choices": [{"message": {"content": "a" * 600}, "finish_reason": "stop"}]}
        with patch.object(generation, "ensure_model", return_value="model"), patch.object(generation, "request_json", return_value=reply) as request:
            with self.assertRaisesRegex(generation.GenerationError, "350–450"):
                generation.generate_passage("English")
            self.assertEqual(request.call_count, 3)

    def test_timeout_and_http_errors_are_actionable(self):
        with patch.object(generation.subprocess, "run", side_effect=subprocess.TimeoutExpired("lms", 1)):
            with self.assertRaises(generation.GenerationError):
                generation.run_lms("lms", "load", "gpt-oss-20b")
        opener = Mock()
        opener.open.side_effect = HTTPError("url", 401, "Unauthorized", {}, None)
        with patch.object(generation, "build_opener", return_value=opener):
            with self.assertRaisesRegex(generation.GenerationError, "authentication"):
                generation.request_json("/v1/chat/completions", {})
