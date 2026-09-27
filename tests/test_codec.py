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
        self.assertEqual(encode("中"), "中".encode("utf-8").join([b"3:", b","]))

    def test_encode_length_prefix_matches_payload(self):
        payload = bytes(range(256))
        encoded = encode(payload)
        declared = int(encoded[:encoded.find(b":")])
        self.assertEqual(declared, len(payload))


class DecodeValidTest(unittest.TestCase):
    def test_decode_single(self):
        self.assertEqual(decode(b"5:hello,"), [b"hello"])

    def test_decode_multiple(self):
        self.assertEqual(decode(b"1:a,1:b,"), [b"a", b"b"])

    def test_decode_empty(self):
        self.assertEqual(decode(b""), [])

    def test_decode_zero_length_item(self):
        self.assertEqual(decode(b"0:,"), [b""])

    def test_decode_leading_zero_length(self):
        self.assertEqual(decode(b"05:hello,"), [b"hello"])
        self.assertEqual(decode(b"00:,"), [b""])

    def test_decode_utf8_content_by_bytes(self):
        self.assertEqual(decode("3:中,"), ["中".encode("utf-8")])

    def test_decode_content_with_arbitrary_bytes(self):
        payload = b"a,b:c\x00\xff\n"
        self.assertEqual(decode(encode(payload)), [payload])

    def test_decode_is_deterministic(self):
        payload = b"3:hello,"
        first = second = None
        for _ in range(2):
            try:
                decode(payload)
            except NetstringError as error:
                result = (error.index, error.offset, str(error))
            if first is None:
                first = result
            else:
                second = result
        self.assertEqual(first, second)


class DecodeErrorTest(unittest.TestCase):
    def assert_error(self, payload, index, offset, message):
        with self.assertRaises(NetstringError) as caught:
            decode(payload)
        error = caught.exception
        self.assertEqual(error.index, index)
        self.assertEqual(error.offset, offset)
        self.assertEqual(str(error), message)

    def test_length_mismatch_reports_declared_and_actual(self):
        self.assert_error(
            b"3:hello,", 0, 5, "第 0 条：长度不符（声明 3，实际 5）（偏移 5）"
        )

    def test_length_mismatch_without_any_comma(self):
        self.assert_error(
            b"2:abcd", 0, 4, "第 0 条：长度不符（声明 2，实际 4）（偏移 4）"
        )

    def test_length_mismatch_on_second_item(self):
        self.assert_error(
            b"1:a,1:bc,", 1, 7, "第 1 条：长度不符（声明 1，实际 2）（偏移 7）"
        )

    def test_missing_trailing_comma(self):
        self.assert_error(b"5:hello", 0, 7, "第 0 条：缺少结尾逗号（偏移 7）")

    def test_missing_trailing_comma_on_second_item(self):
        self.assert_error(b"1:a,1:b", 1, 7, "第 1 条：缺少结尾逗号（偏移 7）")

    def test_missing_colon(self):
        self.assert_error(b"5", 0, 1, "第 0 条：缺少冒号（偏移 1）")

    def test_rejects_plus_sign(self):
        self.assert_error(b"+5:hello,", 0, 0, "第 0 条：非法长度 '+'（偏移 0）")

    def test_rejects_hex_length(self):
        self.assert_error(b"0x5:hello,", 0, 1, "第 0 条：非法长度 'x'（偏移 1）")

    def test_rejects_whitespace_in_length(self):
        self.assert_error(b" 5:hello,", 0, 0, "第 0 条：非法长度 ' '（偏移 0）")
        self.assert_error(b"5 :hello,", 0, 1, "第 0 条：非法长度 ' '（偏移 1）")

    def test_rejects_negative_length(self):
        self.assert_error(b"-1:a,", 0, 0, "第 0 条：非法长度 '-'（偏移 0）")

    def test_rejects_empty_length(self):
        self.assert_error(b":hello,", 0, 0, "第 0 条：非法长度 ':'（偏移 0）")

    def test_rejects_non_digit_length(self):
        self.assert_error(b"x:hello,", 0, 0, "第 0 条：非法长度 'x'（偏移 0）")

    def test_rejects_garbage_between_items(self):
        self.assert_error(
            b"1:a, 1:b,", 1, 4, "第 1 条：非法长度 ' '（偏移 4）"
        )

    def test_declared_length_beyond_remaining(self):
        self.assert_error(
            b"10:hello,", 0, 3,
            "第 0 条：长度超出剩余字节（声明 10，剩余 6）（偏移 3）",
        )

    def test_declared_length_beyond_remaining_no_comma(self):
        self.assert_error(
            b"5:hell", 0, 2,
            "第 0 条：长度超出剩余字节（声明 5，剩余 4）（偏移 2）",
        )

    def test_absurdly_long_length_prefix(self):
        payload = b"9" * 6000 + b":x,"
        with self.assertRaises(NetstringError) as caught:
            decode(payload)
        error = caught.exception
        self.assertEqual(error.index, 0)
        self.assertEqual(error.offset, 6001)
        self.assertIn("长度超出剩余字节", str(error))


class RoundTripTest(unittest.TestCase):
    def test_decode_encode_roundtrip_random_bytes(self):
        rng = random.Random(20260928)
        for _ in range(2000):
            payload = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 64)))
            self.assertEqual(decode(encode(payload)), [payload])

    def test_decode_encode_roundtrip_stream(self):
        rng = random.Random(7)
        items = [
            bytes(rng.randrange(256) for _ in range(rng.randrange(0, 40)))
            for _ in range(500)
        ]
        payload = b"".join(encode(item) for item in items)
        self.assertEqual(decode(payload), items)


if __name__ == "__main__":
    unittest.main()
