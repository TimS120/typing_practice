"""One-off local passages. No chat history, text files, or model unloading."""
from __future__ import annotations

import json
from pathlib import Path
import random
import re
import shutil
import subprocess
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

MODEL_KEY = "gpt-oss-20b"
MODEL_IDENTIFIER = "typing-practice-gpt-oss-20b"
SERVER_URL = "http://127.0.0.1:1234"
MIN_CHARACTERS = 350
MAX_CHARACTERS = 450
TOPICS = (
    "a peculiar museum exhibit", "a repair at a mountain observatory", "a tiny city garden",
    "an unexpected discovery in a library", "a lighthouse keeper's ordinary morning",
    "a traveling baker", "a railway station at dawn", "an unusual local tradition",
    "a curious invention", "an animal adapting to city life", "a forgotten musical instrument",
    "a scientific experiment in a kitchen", "a boat trip on a quiet river", "a neighborhood festival",
    "a craftsperson's workshop", "a market on a rainy day", "a telescope in a village",
    "an expedition to an icy island", "a clockmaker solving a puzzle", "a floating greenhouse",
)


class GenerationError(RuntimeError):
    """An actionable generation failure safe to show in the application."""


def find_lms():
    executable = shutil.which("lms")
    if executable:
        return executable
    local = Path.home() / ".lmstudio" / "bin" / "lms"
    if local.is_file():
        return str(local)
    raise GenerationError("LM Studio's lms CLI was not found. Install it or add it to PATH.")


def run_lms(executable, *arguments, timeout=60):
    try:
        result = subprocess.run([executable, *arguments], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise GenerationError("LM Studio took too long to start or load the model. Try again.") from error
    except OSError as error:
        raise GenerationError(f"Could not run LM Studio: {error}") from error
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-1200:]
        raise GenerationError(f"LM Studio could not {' '.join(arguments[:2])}: {detail}")
    return result.stdout


def request_json(path, payload=None, timeout=180):
    # A local request must not be sent through a configured network proxy.
    opener = build_opener(ProxyHandler({}))
    request = Request(SERVER_URL + path,
                      data=None if payload is None else json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json"})
    try:
        with opener.open(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as error:
        hint = " Disable API authentication for the local server or configure LM Studio accordingly." if error.code == 401 else " Check LM Studio's server and model status."
        raise GenerationError(f"LM Studio returned HTTP {error.code}.{hint}") from error
    except (URLError, TimeoutError, OSError) as error:
        raise GenerationError("Could not reach LM Studio at 127.0.0.1:1234. Check its local server and try again.") from error
    except (ValueError, TypeError) as error:
        raise GenerationError("LM Studio returned an invalid response.") from error


def ensure_model(progress):
    executable = find_lms()
    progress("Starting LM Studio…")
    run_lms(executable, "daemon", "up")
    run_lms(executable, "server", "start", "--port", "1234", "--bind", "127.0.0.1")
    try:
        loaded = json.loads(run_lms(executable, "ps", "--json"))
        available = json.loads(run_lms(executable, "ls", "--llm", "--json"))
        model = next((m for m in available if m.get("modelKey") == MODEL_KEY), None)
        if model is None:
            raise GenerationError("gpt-oss-20b is not downloaded in LM Studio. Download it there, then try again.")
        # Reuse this exact model if already loaded, without changing other models.
        for instance in loaded:
            if instance.get("path") == model.get("path") or instance.get("modelKey") == MODEL_KEY:
                identifier = instance.get("identifier")
                if identifier:
                    return identifier
        progress("Loading gpt-oss-20b…")
        run_lms(executable, "load", MODEL_KEY,
                "--identifier", MODEL_IDENTIFIER, "--context-length", "4096", "--yes", timeout=300)
    except (ValueError, TypeError, AttributeError) as error:
        raise GenerationError("LM Studio returned an invalid model list. Check the installed CLI version.") from error
    return MODEL_IDENTIFIER


def clean_passage(content):
    if not isinstance(content, str):
        raise GenerationError("The model returned no practice text.")
    # Reasoning is never practice text, even if a runtime embeds it in content.
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if "<think>" in content or "<|" in content:
        raise GenerationError("The model returned unfinished reasoning instead of a passage. Try again.")
    if content.startswith('```'):
        content = re.sub(r"^```[^\n]*\n|\n```$", "", content).strip()
    content = unicodedata.normalize("NFC", " ".join(content.split()))
    if not content or any(unicodedata.category(c).startswith("C") for c in content):
        raise GenerationError("The model returned no usable practice text. Try again.")
    return content


def generate_passage(language, progress=lambda message: None):
    if language not in ("English", "German"):
        raise GenerationError("Choose English or German for the generated passage.")
    identifier = ensure_model(progress)
    topic = random.SystemRandom().choice(TOPICS)
    system = (
        "Reasoning: low\n"
        "Write a natural, meaningful typing-practice paragraph with complete sentences. "
        "Return ONLY the paragraph, without a title, explanation, markdown, or character count. "
        "Aim for roughly 400 characters including spaces (350–450). "
        "Estimate the length; do not count individual characters. "
        "Use normal language, without deliberately emphasizing rare characters."
    )
    user = f"Write one paragraph in {language} about {topic}. Use a new random detail."
    # Every call starts a fresh, stateless chat. Bounded revisions avoid clipped sentences.
    for attempt in range(3):
        progress("Generating a fresh passage…" if attempt == 0 else "Adjusting passage length…")
        response = request_json("/v1/chat/completions", {
            "model": identifier,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.9, "max_tokens": 3072, "stream": False,
            "reasoning_effort": "low",
        })
        try:
            choice = response["choices"][0]
            content = choice["message"]["content"]
            passage = clean_passage(content) if content else ""
        except (KeyError, IndexError, TypeError) as error:
            raise GenerationError("LM Studio returned no practice paragraph. Try again.") from error
        if choice.get("finish_reason") != "length" and MIN_CHARACTERS <= len(passage) <= MAX_CHARACTERS:
            return passage
        user = (f"Write a new paragraph in {language} about {topic}. The previous attempt was "
                f"{len(passage)} characters. The result MUST be 350–450 characters including spaces. "
                "Estimate length without counting characters. End with a complete sentence. Return only the paragraph.")
    raise GenerationError("The model did not produce a complete 350–450-character passage. Please try again.")
