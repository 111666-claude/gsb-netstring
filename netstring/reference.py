"""参考实现：逐字节状态机，用来和 codec.decode / NetstringDecoder 对照。

状态：length（读长度数字）→ content（读内容）→ comma（等结尾逗号），
长度对不上时进入 mismatch（扫到下一个逗号才能给出实际长度）。
"""

from .codec import NetstringError

_MAX_LENGTH_DIGITS = 19


def reference_decode(data):
    """逐字节状态机版 decode，错误信息（第几条 + 偏移）与 codec.decode 一致。"""
    if isinstance(data, str):
        data = data.encode("utf-8")
    items = []
    index = 0
    state = "length"
    digits = bytearray()
    declared_text = ""
    remaining = 0
    content = bytearray()
    extra = 0
    n = len(data)
    for i in range(n):
        byte = data[i]
        if state == "length":
            if 0x30 <= byte <= 0x39:
                digits.append(byte)
                continue
            if byte == 0x3A and digits:
                normalized = bytes(digits).lstrip(b"0") or b"0"
                declared_text = normalized.decode("ascii")
                if len(normalized) > _MAX_LENGTH_DIGITS:
                    remaining = None
                else:
                    remaining = int(normalized)
                content = bytearray()
                state = "content" if remaining != 0 else "comma"
                continue
            raise NetstringError(index, i, "非法长度")
        if state == "content":
            content.append(byte)
            if remaining is not None:
                remaining -= 1
                if remaining == 0:
                    state = "comma"
            continue
        if state == "comma":
            if byte == 0x2C:
                items.append(bytes(content))
                index += 1
                digits = bytearray()
                state = "length"
                continue
            state = "mismatch"
            extra = 1
            continue
        # mismatch：已确定长度不符，扫到下一个逗号才能给出实际长度
        if byte == 0x2C:
            raise NetstringError(
                index, i,
                "长度不符（声明 %s，实际 %d）" % (declared_text, len(content) + extra))
        extra += 1
    if state == "length":
        if digits:
            raise NetstringError(index, n, "缺少冒号")
        return items
    if state == "content":
        raise NetstringError(
            index, n,
            "长度不符（声明 %s，实际 %d）" % (declared_text, len(content)))
    if state == "comma":
        raise NetstringError(index, n, "缺少结尾逗号")
    raise NetstringError(
        index, n,
        "长度不符（声明 %s，实际 %d）" % (declared_text, len(content) + extra))
