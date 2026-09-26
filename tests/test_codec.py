import unittest

from netstring.codec import NetstringError, decode, encode


class EncodeTest(unittest.TestCase):
    def test_encode_text(self):
        self.assertEqual(encode("hello"), b"5:hello,")

    def test_encode_bytes(self):
        self.assertEqual(encode(b"\x00\x01"), b"2:\x00\x01,")

    def test_encode_empty(self):
        self.assertEqual(encode(""), b"0:,")


class DecodeTest(unittest.TestCase):
    def test_decode_single(self):
        self.assertEqual(decode(b"5:hello,"), [b"hello"])

    def test_decode_multiple(self):
        self.assertEqual(decode(b"1:a,1:b,"), [b"a", b"b"])

    def test_decode_empty(self):
        self.assertEqual(decode(b""), [])

    def test_decode_rejects_missing_colon(self):
        with self.assertRaises(NetstringError):
            decode(b"hello")

    def test_decode_rejects_bad_length(self):
        with self.assertRaises((NetstringError, ValueError)):
            decode(b"x:hello,")
