import os
import re
import subprocess
import unittest

DAYREC = os.path.join(os.path.dirname(__file__), "..", "dayrec")


class Help(unittest.TestCase):
    def test_prints_the_whole_header_comment(self):
        with open(DAYREC) as f:
            lines = f.read().splitlines()[1:]
        header = []
        for line in lines:
            if not line.startswith("#"):
                break
            header.append(re.sub(r"^# ?", "", line))
        out = subprocess.run(["sh", DAYREC, "help"], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out.rstrip("\n").splitlines(), header)


if __name__ == "__main__":
    unittest.main()
