"""netstring 编解码。"""

from .codec import NetstringError, decode, encode

__all__ = ["NetstringError", "decode", "encode"]
