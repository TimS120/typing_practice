"""Optional wrapping must not change the text, score, or required newlines."""
import unittest

from utils.typing_input import normalize_wrapped_input


class WrappedInputTests(unittest.TestCase):
    def test_space_or_enter_or_both_at_word_wrap(self):
        target = "hello world"
        for typed in (target, "hello\nworld", "hello \nworld", "hello\n world"):
            with self.subTest(typed=typed):
                normalized, offsets = normalize_wrapped_input(target, typed, {6})
                self.assertEqual(normalized, target)
                self.assertEqual(len(offsets), len(target))

    def test_manual_break_inside_wrapped_long_word_does_not_add_a_word(self):
        normalized, offsets = normalize_wrapped_input("abcdefgh", "abcd\nefgh", {4})
        self.assertEqual(normalized, "abcdefgh")
        self.assertEqual(len(normalized.split()), 1)
        self.assertEqual(offsets[4], 5)

    def test_explicit_newline_and_blank_lines_remain_required(self):
        target = "hello world\n\nnext"
        normalized, _ = normalize_wrapped_input(target, "hello\nworld\n\nnext", {6})
        self.assertEqual(normalized, target)
        for typed in ("hello\nworld next", "hello\nworld\nnext"):
            self.assertNotEqual(normalize_wrapped_input(target, typed, {6})[0], target)

    def test_arbitrary_or_repeated_enter_is_not_ignored(self):
        for typed in ("hel\nlo world", "hello \n\nworld", "hello\n\nworld", "\nhello world"):
            self.assertNotEqual(normalize_wrapped_input("hello world", typed, {6})[0], "hello world")

    def test_error_offset_after_optional_enter_points_to_actual_character(self):
        normalized, offsets = normalize_wrapped_input("hello world", "hello \nXorld", {6})
        self.assertEqual(normalized, "hello Xorld")
        self.assertEqual(offsets[6], 7)

    def test_incremental_enter_then_space_does_not_create_a_mismatch(self):
        for typed in ("hello\n", "hello\n ", "hello\n w"):
            normalized, _ = normalize_wrapped_input("hello world", typed, {6})
            self.assertTrue("hello world".startswith(normalized))

    def test_multiple_wraps_and_unicode(self):
        target = "äpfel öl über"
        for typed in ("äpfel\nöl\nüber", "äpfel \nöl \nüber"):
            self.assertEqual(normalize_wrapped_input(target, typed, {6, 9})[0], target)

    def test_tab_and_multiple_spaces_are_preserved(self):
        self.assertEqual(normalize_wrapped_input("one\ttwo", "one\ntwo", {4})[0], "one\ttwo")
        self.assertEqual(normalize_wrapped_input("one  two", "one \ntwo", {5})[0], "one  two")
        self.assertNotEqual(normalize_wrapped_input("one  two", "one\ntwo", {5})[0], "one  two")
