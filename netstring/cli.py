"""命令行入口：编码或解码 netstring。"""

import argparse
import sys

from .codec import NetstringError, decode, encode


def build_parser():
    parser = argparse.ArgumentParser(prog="netstring", description="netstring 编解码")
    parser.add_argument("--encode", dest="encode_text", help="把这段文本编成 netstring")
    parser.add_argument("--decode", dest="decode_text", help="解码这一串 netstring")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.encode_text is not None:
            print(encode(args.encode_text).decode("utf-8"))
            return 0
        if args.decode_text is not None:
            items = decode(args.decode_text)
            for item in items:
                print(item.decode("utf-8", "replace"))
            print("items=%d" % len(items))
            return 0
    except NetstringError as error:
        print("错误：%s" % error, file=sys.stderr)
        return 1
    print("错误：需要 --encode 或 --decode", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
