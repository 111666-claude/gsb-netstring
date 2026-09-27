"""命令行入口：编码或解码 netstring。"""

import argparse
import sys

from .codec import NetstringError, StreamDecoder, decode, encode


def build_parser():
    parser = argparse.ArgumentParser(prog="netstring", description="netstring 编解码")
    parser.add_argument("--encode", dest="encode_text", help="把这段文本编成 netstring")
    parser.add_argument("--decode", dest="decode_text", help="解码这一串 netstring")
    parser.add_argument(
        "--decode-stream",
        action="store_true",
        help="从标准输入流式解码（分块读取，不整块进内存）",
    )
    return parser


def _print_item(item):
    print(item.decode("utf-8", "replace"))


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.encode_text is not None:
            print(encode(args.encode_text).decode("utf-8"))
            return 0
        if args.decode_text is not None:
            items = decode(args.decode_text)
            for item in items:
                _print_item(item)
            print("items=%d" % len(items))
            return 0
        if args.decode_stream:
            decoder = StreamDecoder()
            count = 0
            while True:
                chunk = sys.stdin.buffer.read(65536)
                if not chunk:
                    break
                for item in decoder.feed(chunk):
                    _print_item(item)
                    count += 1
            decoder.finish()
            print("items=%d" % count)
            return 0
    except NetstringError as error:
        print("错误：%s" % error, file=sys.stderr)
        return 1
    print("错误：需要 --encode 或 --decode", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
