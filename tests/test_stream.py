import random
import tracemalloc
import unittest

from netstring.codec import NetstringError, StreamDecoder, decode, decode_chunks, encode


def feed_in_chunks(payload, sizes):
    decoder = StreamDecoder()
    items = []
    pos = 0
    for size in sizes:
        items.extend(decoder.feed(payload[pos:pos + size]))
        pos += size
    items.extend(decoder.feed(payload[pos:]))
    decoder.finish()
    return items


class StreamTest(unittest.TestCase):
    def setUp(self):
        rng = random.Random(7)
        self.items = [
            bytes(rng.randrange(256) for _ in range(rng.randrange(0, 50)))
            for _ in range(2000)
        ]
        self.payload = b"".join(encode(item) for item in self.items)

    def test_byte_by_byte_matches_batch(self):
        sizes = [1] * len(self.payload)
        self.assertEqual(feed_in_chunks(self.payload, sizes), self.items)

    def test_random_chunks_match_batch(self):
        rng = random.Random(99)
        for _ in range(20):
            sizes = []
            remaining = len(self.payload)
            while remaining > 0:
                size = min(remaining, rng.randrange(1, 300))
                sizes.append(size)
                remaining -= size
            self.assertEqual(feed_in_chunks(self.payload, sizes), self.items)

    def test_empty_feeds_are_noop(self):
        decoder = StreamDecoder()
        self.assertEqual(decoder.feed(b""), [])
        self.assertEqual(decoder.feed(b"1:a,"), [b"a"])
        decoder.finish()

    def test_decode_chunks_helper(self):
        chunks = [self.payload[i:i + 7] for i in range(0, len(self.payload), 7)]
        self.assertEqual(list(decode_chunks(chunks)), self.items)

    def test_error_matches_batch_and_is_sticky(self):
        payload = b"1:a,3:hello,"
        batch_error = None
        try:
            decode(payload)
        except NetstringError as error:
            batch_error = error
        self.assertIsNotNone(batch_error)
        decoder = StreamDecoder()
        with self.assertRaises(NetstringError) as caught:
            pos = 0
            while pos < len(payload):
                decoder.feed(payload[pos:pos + 2])
                pos += 2
            decoder.finish()
        stream_error = caught.exception
        self.assertEqual(str(stream_error), str(batch_error))
        self.assertEqual(stream_error.offset, batch_error.offset)
        with self.assertRaises(NetstringError) as again:
            decoder.feed(b"1:x,")
        self.assertEqual(str(again.exception), str(batch_error))

    def test_finish_reports_truncated_tail(self):
        cases = {
            b"5": "第 0 条：缺少冒号（偏移 1）",
            b"5:he": "第 0 条：长度超出剩余字节（声明 5，剩余 2）（偏移 2）",
            b"5:hello": "第 0 条：缺少结尾逗号（偏移 7）",
        }
        for payload, message in cases.items():
            decoder = StreamDecoder()
            decoder.feed(payload)
            with self.assertRaises(NetstringError) as caught:
                decoder.finish()
            self.assertEqual(str(caught.exception), message)

    def test_memory_depends_on_item_not_stream_size(self):
        item = encode(b"x" * 65536)
        decoder = StreamDecoder()
        tracemalloc.start()
        for _ in range(128):
            decoder.feed(item)
        decoder.finish()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertLess(peak, 4 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
