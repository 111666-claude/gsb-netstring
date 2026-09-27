import random
import unittest

from netstring.codec import NetstringError, decode, encode


class EncodeTest(unittest.TestCase):
    def test_encode_text(self):
        self.assertEqual(encode("hello"), b"5:hello,")

    def test_encode_bytes(self):
        self.assertEqual(encode(b"\x00\x01"), b"2:\x00\x01,")

    def test_encode_empty(self):
        self.assertEqual(encode(""), b"0:,")

    def test_encode_utf8_counts_bytes(self):
        self.assertEqual(encode("中文"), "6:中文,".encode("utf-8"))


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


class LengthCheckTest(unittest.TestCase):
    def test_length_mismatch_reports_declared_actual_and_offset(self):
        with self.assertRaises(NetstringError) as ctx:
            decode(b"3:hello,")
        error = ctx.exception
        self.assertEqual(error.index, 0)
        self.assertEqual(error.offset, 7)
        self.assertEqual(str(error), "第 0 条：长度不符（声明 3，实际 5）（偏移 7）")

    def test_declared_exceeds_remaining(self):
        with self.assertRaises(NetstringError) as ctx:
            decode(b"10:abc,")
        self.assertIn("长度不符（声明 10，实际 4）", str(ctx.exception))
        self.assertEqual(ctx.exception.offset, 7)

    def test_huge_declared_length(self):
        with self.assertRaises(NetstringError) as ctx:
            decode(b"999999999999999999999999:x,")
        self.assertIn("长度不符（声明 999999999999999999999999，实际 2）",
                      str(ctx.exception))

    def test_missing_trailing_comma(self):
        with self.assertRaises(NetstringError) as ctx:
            decode(b"5:hello")
        self.assertEqual(str(ctx.exception), "第 0 条：缺少结尾逗号（偏移 7）")

    def test_zero_length_item(self):
        self.assertEqual(decode(b"0:,"), [b""])

    def test_leading_zero_ok(self):
        self.assertEqual(decode(b"05:hello,"), [b"hello"])
        self.assertEqual(decode(b"000:,"), [b""])

    def test_illegal_length_syntax(self):
        for bad in (b"+5:hello,", b"0x5:hello,", b" 5:hello,", b"5 :hello,",
                    b"-1:a,", b":abc,", b"5.0:hello,"):
            with self.assertRaises(NetstringError, msg=repr(bad)) as ctx:
                decode(bad)
            self.assertIn("非法长度", str(ctx.exception))
            self.assertEqual(ctx.exception.index, 0)

    def test_missing_colon_after_digits(self):
        with self.assertRaises(NetstringError) as ctx:
            decode(b"12")
        self.assertEqual(str(ctx.exception), "第 0 条：缺少冒号（偏移 2）")

    def test_extra_bytes_between_items(self):
        with self.assertRaises(NetstringError) as ctx:
            decode(b"1:a, 1:b,")
        self.assertEqual(ctx.exception.index, 1)
        self.assertEqual(ctx.exception.offset, 4)

    def test_error_carries_item_index(self):
        with self.assertRaises(NetstringError) as ctx:
            decode(b"1:a,1:b,2:xy!")
        self.assertEqual(ctx.exception.index, 2)
        self.assertEqual(ctx.exception.offset, 13)

    def test_utf8_content_by_bytes(self):
        self.assertEqual(decode("6:中文,"), ["中文".encode("utf-8")])

    def test_content_may_contain_any_bytes(self):
        payload = b"\x00,:digits 123 \xff"
        self.assertEqual(decode(encode(payload)), [payload])

    def test_roundtrip_arbitrary_bytes(self):
        rng = random.Random(1234)
        for _ in range(300):
            payload = bytes(rng.randrange(256) for _ in range(rng.randrange(80)))
            self.assertEqual(decode(encode(payload)), [payload])

    def test_decode_is_deterministic(self):
        data = b"3:hello,1:a,"
        outcomes = set()
        for _ in range(3):
            try:
                outcomes.add(("ok", tuple(decode(data))))
            except NetstringError as error:
                outcomes.add(("err", error.index, error.offset, str(error)))
        self.assertEqual(len(outcomes), 1)
