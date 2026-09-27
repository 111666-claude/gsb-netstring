import os
import random
import unittest

from netstring.codec import NetstringDecoder, NetstringError, decode, encode


class StreamingTest(unittest.TestCase):
    def test_chunked_matches_batch(self):
        payloads = [os.urandom(n) for n in (0, 1, 5, 100, 70000)]
        data = b"".join(encode(p) for p in payloads)
        for chunk_size in (1, 3, 64, 4096, len(data)):
            decoder = NetstringDecoder()
            got = []
            for i in range(0, len(data), chunk_size):
                got.extend(decoder.feed(data[i:i + chunk_size]))
            got.extend(decoder.finish())
            self.assertEqual(got, payloads, msg="chunk_size=%d" % chunk_size)

    def test_feed_str_and_empty_chunks(self):
        decoder = NetstringDecoder()
        self.assertEqual(decoder.feed(b""), [])
        self.assertEqual(decoder.feed("5:hel"), [])
        self.assertEqual(decoder.feed(b"lo,"), [b"hello"])
        self.assertEqual(decoder.finish(), [])

    def test_memory_bounded_by_item_not_stream(self):
        # 约 100 MB 流转数据：多条小条目，缓冲不应随总量增长
        item = encode(os.urandom(8192))
        decoder = NetstringDecoder()
        count = 0
        for _ in range(12800):
            count += len(decoder.feed(item))
            self.assertLessEqual(len(decoder._buf), len(item))
        self.assertEqual(decoder.finish(), [])
        self.assertEqual(count, 12800)

    def test_single_big_item_streamed(self):
        payload = os.urandom(1 << 20)
        data = encode(payload)
        decoder = NetstringDecoder()
        got = []
        for i in range(0, len(data), 1 << 16):
            got.extend(decoder.feed(data[i:i + (1 << 16)]))
        got.extend(decoder.finish())
        self.assertEqual(got, [payload])

    def test_error_offset_absolute_across_chunks(self):
        decoder = NetstringDecoder()
        self.assertEqual(decoder.feed(b"1:a,"), [b"a"])
        self.assertEqual(decoder.feed(b"1:b,"), [b"b"])
        self.assertEqual(decoder.feed(b"5:hel"), [])
        with self.assertRaises(NetstringError) as ctx:
            decoder.feed(b"lo")  # 仍不完整，等 finish 才判定
            decoder.finish()
        self.assertEqual(ctx.exception.index, 2)
        self.assertEqual(ctx.exception.offset, 15)
        self.assertIn("缺少结尾逗号", str(ctx.exception))

    def test_error_raised_mid_stream(self):
        decoder = NetstringDecoder()
        decoder.feed(b"1:a,")
        with self.assertRaises(NetstringError) as ctx:
            decoder.feed(b"3:hello,")
        self.assertEqual(ctx.exception.index, 1)
        self.assertEqual(str(ctx.exception),
                         "第 1 条：长度不符（声明 3，实际 5）（偏移 11）")

    def test_feed_after_finish_rejected(self):
        decoder = NetstringDecoder()
        decoder.finish()
        with self.assertRaises(ValueError):
            decoder.feed(b"0:,")

    def test_streaming_result_equals_batch(self):
        rng = random.Random(99)
        for _ in range(200):
            parts = [encode(os.urandom(rng.randrange(20)))
                     for _ in range(rng.randrange(6))]
            data = b"".join(parts)
            decoder = NetstringDecoder()
            got = []
            i = 0
            while i < len(data):
                step = rng.randrange(1, 10)
                got.extend(decoder.feed(data[i:i + step]))
                i += step
            got.extend(decoder.finish())
            self.assertEqual(got, decode(data))
