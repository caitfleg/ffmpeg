# Run: uv run --with sherpa-onnx --with numpy python -m unittest discover tests
import importlib.machinery
import importlib.util
import os
import unittest

path = os.path.join(os.path.dirname(__file__), "..", "dayrec-diarize")
loader = importlib.machinery.SourceFileLoader("dayrec_diarize", path)
spec = importlib.util.spec_from_loader("dayrec_diarize", loader)
dd = importlib.util.module_from_spec(spec)
loader.exec_module(dd)


class Label(unittest.TestCase):
    def test_numbers_speakers_by_first_appearance(self):
        turns = [(0, 5, 7), (5, 10, 3)]
        segs = [(0, 4, "hi"), (6, 9, "hello")]
        self.assertEqual(dd.label(segs, turns), [
            "[00:00:00] Speaker 1: hi",
            "[00:00:06] Speaker 2: hello",
        ])

    def test_segment_goes_to_speaker_talking_most(self):
        turns = [(0, 1, 0), (1, 10, 1)]
        self.assertEqual(dd.label([(0, 9, "mostly B")], turns), ["[00:00:00] Speaker 1: mostly B"])

    def test_joins_same_speaker_unless_far_apart(self):
        turns = [(0, 100, 0)]
        segs = [(0, 2, "one"), (3, 4, "two"), (60, 61, "later")]
        self.assertEqual(dd.label(segs, turns), [
            "[00:00:00] Speaker 1: one two",
            "[00:01:00] Speaker 1: later",
        ])

    def test_no_overlap_takes_nearest_turn_close_by(self):
        turns = [(0, 5, 0), (20, 30, 1)]
        self.assertEqual(dd.label([(5.5, 6, "trailing")], turns), ["[00:00:05] Speaker 1: trailing"])

    def test_keeps_speech_with_no_turn_nearby(self):
        turns = [(0, 5, 0)]
        segs = [(0, 4, "hi"), (60, 62, "missed")]
        self.assertEqual(dd.label(segs, turns), [
            "[00:00:00] Speaker 1: hi",
            "[00:01:00] Speaker ?: missed",
        ])

    def test_no_turns_at_all(self):
        self.assertEqual(dd.label([(0, 1, "x")], []), ["[00:00:00] Speaker ?: x"])

    def test_hour_stamp(self):
        self.assertEqual(dd.stamp(3725.9), "01:02:05")


if __name__ == "__main__":
    unittest.main()
