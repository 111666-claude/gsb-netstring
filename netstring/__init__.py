"""netstring 编解码。"""

from .codec import NetstringDecoder, NetstringError, decode, encode

__all__ = ["NetstringDecoder", "NetstringError", "decode", "encode"]
