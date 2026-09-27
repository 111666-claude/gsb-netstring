import contextlib
import io
import unittest
from unittest import mock

from netstring.cli import main


class _FakeStdin:
    def __init__(self, data):
        self.buffer = io.BytesIO(data)


def run_cli(argv, stdin_data=None):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        if stdin_data is None:
            code = main(argv)
        else:
            with mock.patch("sys.stdin", _FakeStdin(stdin_data)):
                code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class CliTest(unittest.TestCase):
    def test_encode(self):
        code, out, _ = run_cli(["--encode", "hello"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "5:hello,\n")

    def test_decode(self):
        code, out, _ = run_cli(["--decode", "5:hello,"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "hello\nitems=1\n")

    def test_decode_multiple(self):
        code, out, _ = run_cli(["--decode", "1:a,1:b,"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "a\nb\nitems=2\n")

    def test_decode_length_mismatch(self):
        code, _, err = run_cli(["--decode", "3:hello,"])
        self.assertEqual(code, 1)
        self.assertIn("第 0 条：长度不符（声明 3，实际 5）（偏移 5）", err)

    def test_decode_missing_comma(self):
        code, _, err = run_cli(["--decode", "5:hello"])
        self.assertEqual(code, 1)
        self.assertIn("第 0 条：缺少结尾逗号（偏移 7）", err)

    def test_decode_stream(self):
        payload = b"5:hello," * 100
        code, out, _ = run_cli(["--decode-stream"], stdin_data=payload)
        self.assertEqual(code, 0)
        self.assertEqual(out, "hello\n" * 100 + "items=100\n")

    def test_decode_stream_error(self):
        code, _, err = run_cli(["--decode-stream"], stdin_data=b"1:a,9:b,")
        self.assertEqual(code, 1)
        self.assertIn("第 1 条", err)

    def test_no_arguments(self):
        code, _, err = run_cli([])
        self.assertEqual(code, 2)
        self.assertIn("需要 --encode 或 --decode", err)


if __name__ == "__main__":
    unittest.main()
