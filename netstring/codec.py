"""netstring：长度前缀 + 冒号 + 内容 + 逗号。只用标准库。

口径：
- 长度按字节计算，内容可为任意字节；长度前缀只允许十进制数字（前导零合法）。
- 长度必须与内容字节数一致；每条必须以逗号结尾；多条之间不许有多余字节。
- 所有错误都带「第几条（0 起）+ 字节偏移」；空输入返回空列表。
"""


class NetstringError(Exception):
    """netstring 不合法。带条目序号 index（0 起）与字节偏移 offset。"""

    def __init__(self, index, offset, detail):
        self.index = index
        self.offset = offset
        self.detail = detail
        message = "第 %d 条：%s（偏移 %d）" % (index, detail, offset)
        super().__init__(message)
        self.message = message


def _describe_byte(byte):
    """把出错字节描述成人能看懂的一小段。"""
    if 0x20 <= byte < 0x7F:
        return "'%s'" % chr(byte)
    return "0x%02x" % byte


_DECLARED_CAP = (1 << 63) - 1


def _accumulate_length(value, digit):
    """累加长度数字；超过上限就饱和，避免天文数字撑爆 int 格式化。"""
    if value >= _DECLARED_CAP:
        return _DECLARED_CAP, True
    value = value * 10 + digit
    if value >= _DECLARED_CAP:
        return _DECLARED_CAP, True
    return value, False


def _format_declared(value, capped):
    return "≥%d" % value if capped else "%d" % value


def encode(payload):
    """把字节串编成 netstring；长度前缀等于 payload 的字节数。"""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return b"%d:%s," % (len(payload), payload)


_STATE_LENGTH = 0
_STATE_CONTENT = 1
_STATE_COMMA = 2
_STATE_OVERFLOW = 3


class StreamDecoder:
    """增量解码器：feed(chunk) 喂一块解一块，finish() 收尾。

    内存只与单条长度相关：只缓存当前条目的内容；长度不符时向后扫描
    逗号只为数字节数（计数字节，不缓存字节），100 MB 流也不必整块进内存。
    """

    def __init__(self):
        self._state = _STATE_LENGTH
        self._declared = 0
        self._declared_capped = False
        self._has_digits = False
        self._content = bytearray()
        self._index = 0
        self._offset = 0
        self._start = 0
        self._comma_at = 0
        self._overflow = 0
        self._error = None

    def _fail(self, offset, detail):
        self._error = NetstringError(self._index, offset, detail)
        raise self._error

    def feed(self, chunk):
        """喂入一块字节，返回本块中完整解出的条目列表。"""
        if self._error is not None:
            raise self._error
        if isinstance(chunk, str):
            chunk = chunk.encode("utf-8")
        items = []
        pos = 0
        end = len(chunk)
        while pos < end:
            if self._state == _STATE_LENGTH:
                byte = chunk[pos]
                at = self._offset
                self._offset = at + 1
                pos += 1
                if 0x30 <= byte <= 0x39:
                    self._has_digits = True
                    self._declared, capped = _accumulate_length(
                        self._declared, byte - 0x30
                    )
                    self._declared_capped = self._declared_capped or capped
                elif not self._has_digits or byte != 0x3A:
                    self._fail(at, "非法长度 %s" % _describe_byte(byte))
                else:
                    self._start = self._offset
                    self._state = _STATE_CONTENT
            elif self._state == _STATE_CONTENT:
                need = self._declared - len(self._content)
                take = min(need, end - pos)
                if take:
                    self._content += chunk[pos:pos + take]
                    pos += take
                    self._offset += take
                if len(self._content) == self._declared:
                    self._state = _STATE_COMMA
            elif self._state == _STATE_COMMA:
                byte = chunk[pos]
                at = self._offset
                self._offset = at + 1
                pos += 1
                if byte == 0x2C:
                    items.append(bytes(self._content))
                    self._content = bytearray()
                    self._state = _STATE_LENGTH
                    self._declared = 0
                    self._declared_capped = False
                    self._has_digits = False
                    self._index += 1
                else:
                    self._comma_at = at
                    self._overflow = 1
                    self._state = _STATE_OVERFLOW
            else:
                nxt = chunk.find(b",", pos)
                if nxt < 0:
                    self._overflow += end - pos
                    self._offset += end - pos
                    pos = end
                else:
                    self._overflow += nxt - pos
                    actual = self._declared + self._overflow
                    self._fail(
                        self._comma_at,
                        "长度不符（声明 %s，实际 %d）"
                        % (self._declared_text(), actual),
                    )
        if self._state == _STATE_CONTENT and len(self._content) == self._declared:
            self._state = _STATE_COMMA
        return items

    def _declared_text(self):
        return _format_declared(self._declared, self._declared_capped)

    def finish(self):
        """声明输入结束：必须正好停在条目边界，否则报错。"""
        if self._error is not None:
            raise self._error
        if self._state == _STATE_LENGTH:
            if self._has_digits:
                self._fail(self._offset, "缺少冒号")
        elif self._state == _STATE_CONTENT:
            self._fail(
                self._start,
                "长度超出剩余字节（声明 %s，剩余 %d）"
                % (self._declared_text(), len(self._content)),
            )
        elif self._state == _STATE_COMMA:
            self._fail(self._offset, "缺少结尾逗号")
        else:
            actual = self._declared + self._overflow
            self._fail(
                self._comma_at,
                "长度不符（声明 %s，实际 %d）" % (self._declared_text(), actual),
            )


def decode(text):
    """解码一串 netstring，按顺序返回条目列表。空输入返回空列表。"""
    if isinstance(text, str):
        text = text.encode("utf-8")
    decoder = StreamDecoder()
    items = decoder.feed(text)
    decoder.finish()
    return items


def decode_chunks(chunks):
    """对字节块可迭代对象做流式解码，逐条 yield 内容。"""
    decoder = StreamDecoder()
    for chunk in chunks:
        for item in decoder.feed(chunk):
            yield item
    decoder.finish()
