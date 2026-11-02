"""Minimal S-expression reader/writer for KiCad files."""
import re

_TOKEN = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')


class Q(str):
    """A string that must be written quoted."""


def parse(text):
    stack, cur = [], []
    pos = 0
    while True:
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        lp, rp, s, atom = m.groups()
        if lp:
            stack.append(cur)
            cur = []
        elif rp:
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif s is not None:
            cur.append(Q(s[1:-1].replace('\\"', '"').replace("\\\\", "\\")))
        else:
            cur.append(atom)
    return cur[0]


def dump(node, indent=0):
    if isinstance(node, list):
        simple = all(not isinstance(x, list) for x in node)
        if simple:
            return "(" + " ".join(dump(x) for x in node) + ")"
        out = "(" + " ".join(dump(x) for x in node if not isinstance(x, list))
        for x in node:
            if isinstance(x, list):
                out += "\n" + "\t" * (indent + 1) + dump(x, indent + 1)
        return out + "\n" + "\t" * indent + ")"
    if isinstance(node, Q):
        return '"' + node.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(node, str) and len(node) == 36 and node.count("-") == 4:
        return '"' + node + '"'   # uuids are quoted
    if isinstance(node, float):
        return f"{node:.4f}".rstrip("0").rstrip(".")
    return str(node)


def find(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def first(node, key):
    r = find(node, key)
    return r[0] if r else None
