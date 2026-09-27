"""netstring：长度前缀 + 冒号 + 内容 + 逗号。只用标准库。"""

_DIGIT_0 = ord("0")
_DIGIT_9 = ord("9")
_COLON = ord(":")
_COMMA = ord(",")

# 长度前缀最多 19 位有效数字；位数再多的声明不可能对应内存中真实存在的内容，
# 直接按「声明远超剩余字节」处理，也避开 int() 的位数上限。
_MAX_LENGTH_DIGITS = 19


class NetstringError(Exception):
    """netstring 不合法。带第几条（index，从 0 计）与字节偏移（offset，从 0 计）。"""

    def __init__(self, index, offset, reason):
        self.index = index
        self.offset = offset
        self.reason = reason
        self.message = "第 %d 条：%s（偏移 %d）" % (index, reason, offset)
        super().__init__(self.message)


def encode(payload):
    """把字节串编成 netstring；长度前缀等于 payload 的字节数。"""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return b"%d:%s," % (len(payload), payload)


def _parse(data, index, final, base):
    """从 data 起点尽量解析完整条目，返回 (items, consumed, next_index)。

    final=False 时遇到不完整的尾部就停下等更多数据；final=True 时报错。
    确定的错误（非法长度、长度不符等）立即抛 NetstringError，
    报错偏移一律是 base + 局部偏移。
    """
    items = []
    at = 0
    n = len(data)
    while at < n:
        p = at
        while p < n and _DIGIT_0 <= data[p] <= _DIGIT_9:
            p += 1
        if p == at:
            raise NetstringError(index, base + at, "非法长度")
        if p == n:
            if not final:
                break
            raise NetstringError(index, base + n, "缺少冒号")
        if data[p] != _COLON:
            raise NetstringError(index, base + p, "非法长度")
        normalized = data[at:p].lstrip(b"0") or b"0"
        declared_text = bytes(normalized).decode("ascii")
        if len(normalized) > _MAX_LENGTH_DIGITS:
            declared = None
        else:
            declared = int(normalized)
        start = p + 1
        if declared is None or start + declared > n:
            if not final:
                break
            raise NetstringError(
                index, base + n,
                "长度不符（声明 %s，实际 %d）" % (declared_text, n - start))
        end = start + declared
        if end == n:
            if not final:
                break
            raise NetstringError(index, base + end, "缺少结尾逗号")
        if data[end] == _COMMA:
            items.append(bytes(data[start:end]))
            at = end + 1
            index += 1
            continue
        # 前 declared 个字节按声明就是内容，从声明内容末尾之后找逗号
        comma = data.find(b",", end)
        if comma < 0:
            if not final:
                break
            raise NetstringError(
                index, base + n,
                "长度不符（声明 %s，实际 %d）" % (declared_text, n - start))
        raise NetstringError(
            index, base + comma,
            "长度不符（声明 %s，实际 %d）" % (declared_text, comma - start))
    return items, at, index


def decode(text):
    """解码一串 netstring，按顺序返回条目（bytes 列表）。空输入返回 []。"""
    if isinstance(text, str):
        text = text.encode("utf-8")
    items, _, _ = _parse(text, 0, True, 0)
    return items


class NetstringDecoder:
    """增量解码器：feed 一块解一块，内存占用只与当前这一条的长度相关。"""

    def __init__(self):
        self._buf = bytearray()
        self._base = 0
        self._index = 0
        self._finished = False

    def feed(self, chunk):
        """喂一块数据，返回本次解出的完整条目（bytes 列表）。"""
        if self._finished:
            raise ValueError("解码器已 finish，不能再 feed")
        if isinstance(chunk, str):
            chunk = chunk.encode("utf-8")
        self._buf += chunk
        items, consumed, self._index = _parse(
            self._buf, self._index, False, self._base)
        if consumed:
            del self._buf[:consumed]
            self._base += consumed
        return items

    def finish(self):
        """收尾：返回剩余条目；尾部不完整则抛 NetstringError。"""
        if self._finished:
            raise ValueError("解码器已 finish")
        self._finished = True
        items, consumed, self._index = _parse(
            self._buf, self._index, True, self._base)
        if consumed:
            del self._buf[:consumed]
            self._base += consumed
        return items
