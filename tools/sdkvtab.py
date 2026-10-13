#!/usr/bin/env python3
"""The virtual-function order of an LT2 SDK interface, read off its header.

A vtable's slots are the class's virtuals in declaration order, base class
first, a virtual destructor taking the slot where it is declared. That makes
the SDK headers (src/Engine/sdk/inc, NOLF2's) a slot-by-slot NAME list for every engine
interface the game DLLs call -- ILTClient, ILTServer, ILTCommon, ILTModel,
ILTMessage... -- which is the check placement-by-bytes cannot give: two
same-shape one-line wrappers (WriteCompVector / WriteCompRotation) are told
apart by their names and by nothing else.

Usage:
  sdkvtab.py <Class> [--inc=DIR]   print slot, name

--inc reads another header tree instead (the Jupiter SDK's, or
../fear/Dev/Source/runtime/sdk/inc for comparison).
"""
import os
import re
import sys

INC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "src", "Engine", "sdk", "inc")
for _a in list(sys.argv[1:]):
    if _a.startswith("--inc="):
        INC = _a.split("=", 1)[1]
        sys.argv.remove(_a)


def _strip(src):
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"//[^\n]*", " ", src)
    # drop `#if 0` blocks
    out, skip = [], 0
    for line in src.split("\n"):
        t = line.strip()
        if skip:
            if t.startswith("#if"):
                skip += 1
            elif t.startswith("#endif"):
                skip -= 1
            elif t.startswith("#else") and skip == 1:
                skip = 0
            continue
        if re.match(r"#\s*if\s+0\b", t):
            skip = 1
            continue
        out.append(line)
    return "\n".join(out)


_cache = {}


def _sources():
    if not _cache:
        for f in os.listdir(INC):
            if f.endswith(".h"):
                _cache[f] = _strip(open(os.path.join(INC, f), errors="replace").read())
    return _cache


def _body(cls):
    for f, src in _sources().items():
        m = re.search(r"\bclass\s+%s\b\s*(:\s*public\s+(\w+))?\s*\{" % re.escape(cls), src)
        if not m:
            continue
        i = m.end()
        depth = 1
        j = i
        while depth and j < len(src):
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
            j += 1
        return m.group(2), src[i:j - 1]
    return None, None


def virtuals(cls):
    """[name, ...] in vtable order; '~' for the destructor."""
    base, body = _body(cls)
    if body is None:
        raise KeyError(cls)
    out = virtuals(base) if base else []
    # flatten nested braces (inline bodies) so declarations are one level
    flat, depth = [], 0
    for ch in body:
        if ch == "{":
            depth += 1
            flat.append(";" if depth == 1 else "")
            continue
        if ch == "}":
            depth -= 1
            continue
        if depth == 0:
            flat.append(ch)
    for decl in "".join(flat).split(";"):
        if not re.search(r"\bvirtual\b", decl):
            continue
        decl = decl[re.search(r"\bvirtual\b", decl).end():]
        m = re.search(r"(~?\w+)\s*\(", decl)
        if not m:
            continue
        name = m.group(1)
        if name.startswith("~"):
            name = "~"
        # an override of a base virtual keeps the base slot
        if name in out and name != "~":
            continue
        if name == "~" and "~" in out:
            continue
        out.append(name)
    return out


if __name__ == "__main__":
    for k, n in enumerate(virtuals(sys.argv[1])):
        print(k, n)
