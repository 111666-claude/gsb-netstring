"""参考实现：逐字节状态机解码，独立于 codec.StreamDecoder 编写。

用途：在对照测试里验证主实现对合法与畸形输入给出相同结果与相同错误偏移。
"""

from .codec import (
    NetstringError,
    _accumulate_length,
    _describe_byte,
    _format_declared,
)

_LENGTH = 0
_CONTENT = 1
_COMMA = 2


def decode_reference(text):
    """逐字节状态机解码；错误信息、条目序号、偏移与 codec.decode 一致。"""
    if isinstance(text, str):
        text = text.encode("utf-8")

    items = []
    state = _LENGTH
    declared = 0
    declared_capped = False
    has_digits = False
    start = 0
    index = 0
    pos = 0
    total = len(text)

    while pos < total:
        byte = text[pos]

        if state == _LENGTH:
            if 0x30 <= byte <= 0x39:
                has_digits = True
                declared, capped = _accumulate_length(declared, byte - 0x30)
                declared_capped = declared_capped or capped
                pos += 1
            elif not has_digits or byte != 0x3A:
                raise NetstringError(
                    index, pos, "非法长度 %s" % _describe_byte(byte)
                )
            else:
                start = pos + 1
                state = _CONTENT
                pos += 1

        elif state == _CONTENT:
            if pos - start < declared:
                pos += 1
            else:
                state = _COMMA

        else:
            if byte == 0x2C:
                items.append(text[start:pos])
                index += 1
                state = _LENGTH
                declared = 0
                declared_capped = False
                has_digits = False
                pos += 1
            else:
                scan = pos
                while scan < total and text[scan] != 0x2C:
                    scan += 1
                raise NetstringError(
                    index,
                    pos,
                    "长度不符（声明 %s，实际 %d）"
                    % (_format_declared(declared, declared_capped), scan - start),
                )

    if state == _LENGTH:
        if has_digits:
            raise NetstringError(index, total, "缺少冒号")
    elif state == _CONTENT:
        if total - start < declared:
            raise NetstringError(
                index,
                start,
                "长度超出剩余字节（声明 %s，剩余 %d）"
                % (_format_declared(declared, declared_capped), total - start),
            )
        raise NetstringError(index, total, "缺少结尾逗号")
    else:
        raise NetstringError(index, total, "缺少结尾逗号")

    return items
