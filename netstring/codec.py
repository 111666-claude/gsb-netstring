"""netstring：长度前缀 + 冒号 + 内容 + 逗号。只用标准库。"""


class NetstringError(Exception):
    """netstring 不合法。缺陷：只带一句说明，不带字节偏移。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def encode(payload):
    """把字节串编成 netstring。"""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return b"%d:%s," % (len(payload), payload)


def decode(text):
    """解码一串 netstring。

    缺陷：不校验长度与内容是否一致（多退少补都放过），也不校验结尾逗号。
    """
    if isinstance(text, str):
        text = text.encode("utf-8")
    items = []
    at = 0
    while at < len(text):
        colon = text.find(b":", at)
        if colon < 0:
            raise NetstringError("缺少冒号")
        length = int(text[at:colon])
        start = colon + 1
        end = start + length
        items.append(text[start:end])
        at = end + 1
    return items
