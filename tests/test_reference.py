import random
import unittest

from netstring.codec import NetstringError, StreamDecoder, decode, encode
from netstring.reference import decode_reference

SAMPLES = [
    b"",
    b"0:,",
    b"5:hello,",
    b"05:hello,",
    b"1:a,1:b,0:,",
    b"3:hello,",
    b"5:hello",
    b"5:hell",
    b"10:hello,",
    b"5",
    b"+5:hello,",
    b"-1:a,",
    b"0x5:hello,",
    b" 5:hello,",
    b"5 :hello,",
    b"x:hello,",
    b":hello,",
    b"1:a, 1:b,",
    b"1:a,1:b",
    b"2:abcd",
    b"1:a,1:bc,",
    b"0:x,",
    "3:中,".encode("utf-8"),
    b"4:\xe4\xb8\xad,",
    b"3:,",
    b"1:,",
    b",",
    b":",
    b"9" * 100 + b":",
    b"9" * 6000 + b":x,",
]


def run_one(func, payload):
    try:
        return ("ok", func(payload))
    except NetstringError as error:
        return ("err", error.index, error.offset, str(error))


def run_streamed(payload, chunk_sizes):
    decoder = StreamDecoder()
    items = []
    pos = 0
    try:
        for size in chunk_sizes:
            items.extend(decoder.feed(payload[pos:pos + size]))
            pos += size
        items.extend(decoder.feed(payload[pos:]))
        decoder.finish()
        return ("ok", items)
    except NetstringError as error:
        return ("err", error.index, error.offset, str(error))


class SampleDifferentialTest(unittest.TestCase):
    def check_all_agree(self, payload):
        expected = run_one(decode, payload)
        self.assertEqual(
            run_one(decode_reference, payload), expected,
            "参考实现与主实现不一致：%r" % payload[:60],
        )
        rng = random.Random(len(payload))
        chunk_sizes = [rng.randrange(1, 8) for _ in range(len(payload) + 1)]
        self.assertEqual(
            run_streamed(payload, chunk_sizes), expected,
            "流式与批量不一致：%r" % payload[:60],
        )

    def test_samples(self):
        for payload in SAMPLES:
            self.check_all_agree(payload)


class RandomDifferentialTest(unittest.TestCase):
    def test_random_valid_stream_10k_items(self):
        rng = random.Random(20260928)
        items = [
            bytes(rng.randrange(256) for _ in range(rng.randrange(0, 40)))
            for _ in range(10000)
        ]
        payload = b"".join(encode(item) for item in items)
        self.assertEqual(decode(payload), items)
        self.assertEqual(decode_reference(payload), items)

    def test_random_malformed_streams(self):
        rng = random.Random(1234)
        alphabet = b"0123456789:,+x- \x00\xff"
        for _ in range(10000):
            kind = rng.randrange(6)
            if kind == 0:
                items = [
                    bytes(rng.randrange(256) for _ in range(rng.randrange(0, 12)))
                    for _ in range(rng.randrange(0, 6))
                ]
                payload = b"".join(encode(item) for item in items)
                cut = rng.randrange(0, len(payload) + 1)
                payload = payload[:cut]
            elif kind == 1:
                payload = bytes(
                    alphabet[rng.randrange(len(alphabet))]
                    for _ in range(rng.randrange(0, 20))
                )
            elif kind == 2:
                payload = encode(bytes(rng.randrange(256) for _ in range(8)))
                at = rng.randrange(len(payload))
                payload = payload[:at] + bytes([rng.randrange(256)]) + payload[at + 1:]
            elif kind == 3:
                declared = rng.randrange(0, 12)
                actual = rng.randrange(0, 12)
                payload = (b"%d:" % declared) + bytes(
                    rng.randrange(256) for _ in range(actual)
                ) + (b"," if rng.randrange(2) else b"")
            elif kind == 4:
                payload = b"%d:%s," % (
                    rng.randrange(0, 20),
                    bytes(rng.randrange(256) for _ in range(rng.randrange(0, 20))),
                )
            else:
                prefix = encode(b"ok") * rng.randrange(0, 4)
                junk = bytes(
                    alphabet[rng.randrange(len(alphabet))]
                    for _ in range(rng.randrange(1, 8))
                )
                payload = prefix + junk
            expected = run_one(decode, payload)
            actual = run_one(decode_reference, payload)
            self.assertEqual(
                actual, expected,
                "第 %d 条用例不一致：%r" % (_, payload[:60]),
            )


if __name__ == "__main__":
    unittest.main()
