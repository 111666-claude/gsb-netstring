import random
import unittest

from netstring.codec import NetstringDecoder, NetstringError, decode, encode
from netstring.reference import reference_decode

SAMPLES = [
    b"",
    b"0:,",
    b"00:,",
    b"5:hello,",
    b"05:hello,",
    b"3:hello,",
    b"5:hello",
    b"10:abc,",
    b"1:a,1:b,",
    b"1:a, 1:b,",
    b"1:a,,",
    b"+5:hello,",
    b"-1:a,",
    b"0x5:hello,",
    b" 5:hello,",
    b"5 :hello,",
    b":abc,",
    b"12",
    b"hello",
    b"2:he,lo,",
    b"5:he,lo,",
    b"1:\x00,",
    b"999999999999999999999999:x,",
    b"3:ab",
    b"3:abcdef",
    "6:中文,".encode("utf-8"),
    "4:中文,".encode("utf-8"),
]


def outcome(fn, data):
    try:
        return ("ok", fn(data))
    except NetstringError as error:
        return ("err", error.index, error.offset, str(error))


def random_stream(rng):
    parts = []
    for _ in range(rng.randrange(5)):
        size = rng.randrange(12)
        payload = bytes(rng.randrange(256) for _ in range(size))
        if rng.random() < 0.3:
            payload += rng.choice([b",", b":", b"123", b" ", "中".encode("utf-8")])
        parts.append(encode(payload))
    data = b"".join(parts)
    if data and rng.random() < 0.6:
        kind = rng.randrange(6)
        if kind == 0:
            data = data[:rng.randrange(len(data) + 1)]
        elif kind == 1:
            pos = rng.randrange(len(data))
            data = data[:pos] + bytes([rng.randrange(256)]) + data[pos + 1:]
        elif kind == 2:
            commas = [i for i, b in enumerate(data) if b == 0x2C]
            if commas:
                pos = rng.choice(commas)
                data = data[:pos] + data[pos + 1:]
        elif kind == 3:
            pos = rng.randrange(len(data) + 1)
            junk = rng.choice([b"+", b" ", b"x", b"-", b":", b","])
            data = data[:pos] + junk + data[pos:]
        elif kind == 4:
            data += rng.choice([b"+5:", b" ", b"1", b":", b",", b"2:ab"])
        else:
            digits = [i for i, b in enumerate(data) if 0x30 <= b <= 0x39]
            if digits:
                pos = rng.choice(digits)
                data = data[:pos] + bytes([rng.randrange(0x30, 0x3A)]) + data[pos + 1:]
    return data


def streamed_outcome(decoder_factory, data, rng):
    decoder = decoder_factory()
    got = []
    try:
        i = 0
        while i < len(data):
            step = rng.randrange(1, max(2, len(data) // 2 + 1))
            got.extend(decoder.feed(data[i:i + step]))
            i += step
        got.extend(decoder.finish())
        return ("ok", got)
    except NetstringError as error:
        return ("err", error.index, error.offset, str(error))


class ReferenceCrossCheckTest(unittest.TestCase):
    def test_samples_match(self):
        for sample in SAMPLES:
            self.assertEqual(outcome(decode, sample),
                             outcome(reference_decode, sample),
                             msg=repr(sample))

    def test_random_streams_match(self):
        rng = random.Random(20260928)
        for _ in range(10000):
            data = random_stream(rng)
            self.assertEqual(outcome(decode, data),
                             outcome(reference_decode, data),
                             msg=repr(data))

    def test_streaming_matches_reference(self):
        rng = random.Random(7)
        for _ in range(2000):
            data = random_stream(rng)
            self.assertEqual(streamed_outcome(NetstringDecoder, data, rng),
                             outcome(reference_decode, data),
                             msg=repr(data))
