# -*- coding: utf-8 -*-
r"""ЛЁГКАЯ ПРОВЕРКА JS БЕЗ NODE (dev\js_balance.py)

Живая причина: в системе нет `node`, а после каждой правки витрины надо убедиться, что скрипт цел.
Модуль убирает то, что мешает счёту — строки, комментарии, регулярки, а шаблонные строки (`…`)
превращает в `T`, содержимое `${ … }` — в обычные круглые скобки. После этого проверяется парность
`{ } ( ) [ ]` со стеком.

`balance(src)` → None (всё сбалансировано) либо текст первой ошибки.
"""
RE_OPEN = "([,=:[!&|?{};+-*%~^<>"   # если '/' идёт сразу после такого символа — это регулярка
OUT = []


def _clean(src):
    n = len(src)
    out = OUT
    out.clear()
    i = 0
    prev = [""]

    def code(i, stop_brace):
        depth = 0
        while i < n:
            c = src[i]
            nx = src[i + 1] if i + 1 < n else ""
            if c in "'\"":
                q = c
                j = i + 1
                while j < n and src[j] != q:
                    j += 2 if src[j] == "\\" else 1
                out.append("S")
                prev[0] = "S"
                i = j + 1
                continue
            if c == "`":
                i += 1
                while i < n:
                    if src[i] == "\\":
                        i += 2
                        continue
                    if src[i] == "`":
                        i += 1
                        break
                    if src[i] == "$" and i + 1 < n and src[i + 1] == "{":
                        out.append("(")
                        i = code(i + 2, True)
                        out.append(")")
                        prev[0] = ")"
                        continue
                    i += 1
                out.append("T")
                prev[0] = "T"
                continue
            if c == "/" and nx == "/":
                j = src.find("\n", i)
                i = n if j < 0 else j
                continue
            if c == "/" and nx == "*":
                j = src.find("*/", i)
                i = n if j < 0 else j + 2
                continue
            if c == "/" and (prev[0] == "" or prev[0] in RE_OPEN):
                j = i + 1
                incls = False
                while j < n:
                    if src[j] == "\\":
                        j += 2
                        continue
                    if src[j] == "\n":
                        break
                    if src[j] == "[":
                        incls = True
                    elif src[j] == "]":
                        incls = False
                    elif src[j] == "/" and not incls:
                        j += 1
                        break
                    j += 1
                out.append("R")
                prev[0] = "R"
                i = j
                continue
            if c == "}" and stop_brace and depth == 0:
                return i + 1
            if c in "{[(":
                depth += 1
            elif c in "}])":
                depth = max(0, depth - 1)
            out.append(c)
            if not c.isspace():
                prev[0] = c
            i += 1
        return i

    code(0, False)
    return "".join(out)


def balance(src):
    t = _clean(src)
    st = []
    pairs = {"}": "{", ")": "(", "]": "["}
    for idx, c in enumerate(t):
        if c in "{[(":
            st.append(c)
        elif c in pairs:
            if st and st[-1] == pairs[c]:
                st.pop()
            else:
                return "лишняя закрывающая %r (строка ~%d)" % (c, t[:idx].count("\n") + 1)
    if st:
        return "не закрыто: %s" % "".join(st[-8:])
    return None
