# netstring

netstring 编解码（长度前缀 + 冒号 + 内容 + 逗号），只用 Python 标准库。

```
python3 -m netstring.cli --encode hello
python3 -m netstring.cli --decode "5:hello,"
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- 一条 netstring 是 `长度:内容,`，长度是**字节数**（UTF-8 中文按字节算），内容里可以出现任意字节。
- **长度必须与内容严格一致**：`3:hello,` 声明 3 字节却给了 5 字节，要报「第 0 条：长度不符（声明 3，实际 5）」
  并给出偏移；现在读到末尾找不到下一个冒号，报的是含糊的「缺少冒号」。
- **结尾必须有逗号**：`5:hello` 缺逗号要报「第 0 条：缺少结尾逗号（偏移 7）」；现在照样返回 `hello`。
- 一次可以解码多条，按顺序返回；长度前缀不允许多余前导零以外的东西（`05:hello,` 合法、`+5:` 非法），
  多条之间不留空白的多余字节也要报错。
- 不变量：`decode(encode(x)) == [x]`（任意字节串）；`encode` 的长度前缀等于 `len(payload)`；
  同一输入重复解码结果相同。
- 规模：100 MB 的流转数据要单遍流式解码，内存 O(单条长度)，不许整块读进内存再切。

## 现在的行为

- `decode` 只按声明长度切片，**不校验**长度与内容是否一致：`3:hello,` 会错位到后面的字节上再报
  「缺少冒号」，`5:hello` 干脆忽略缺失的逗号直接返回内容。
- 没有偏移信息：所有错误都只有一句话。
- 不处理前导零与 `+`/空白等非法长度写法；也不做流式（调用方必须整串传进来）。

## 计划新增的能力

```
--encode 文本    编成 netstring 并打印
--decode 串      逐条解码并打印
```

## 输出

```
5:hello,
hello
items=1
```

## 目录

```
netstring/codec.py   编解码与校验
netstring/cli.py     命令行入口
tests/               unittest 用例
```
