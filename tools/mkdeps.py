#!/usr/bin/env python3
"""Header dependencies for build/build.mk, which VC6 cannot report.

VC6's compilers have no /showIncludes (it arrived in VS2005), so the
Makefile cannot learn from a compile which headers an object depends on.
This finds them the way the compiler does: every `#include` line of the
source and, recursively, of every header it names, resolved like MSVC --

  "name"  the including file's directory, then the source file's, then the
          /I directories (relative to the compile's working directory), then
          the project headers on INCLUDE (src/nolf2src/)
  <name>  the /I directories, then the project headers on INCLUDE

-- case-insensitively, as on Windows, with `\\` as a separator. The
toolchains' own headers are never on the list (they do not change), and a
name that resolves nowhere is skipped, as the compiler would skip it under
an #if it is not built with. Conditionals are ignored: an #include inside
any #if counts. That can add a dependency that is not real, never miss one.

A resource script (an .rc source; rc.exe cannot list what it reads
either) depends on the same, its `/i` directories taken for /I, and also on
what it `rcinclude`s, on the files its resources name (`IDB_X BITMAP
DISCARDABLE "bmp\\x.bmp"`: searched for in the naming file's directory, the
script's, the working directory and the /i directories), recursively through
every script and header it includes, and on every file in its own directory
and in each /i directory.

  tools/mkdeps.py <spec> <out.mk>

<spec> has one line per object: `obj<TAB>cwd<TAB>source<TAB>args`: the
object and the compile's working directory relative to the tree root (the
current directory), and the source and the compiler arguments as the
compile spells them (Windows paths relative to the working directory; the
/I directories are taken from the arguments). <out.mk> gets
`obj: source header...` rules, plus an empty rule per header so that a
deleted header does not stop make (like gcc's -MP); it is rewritten only
when its content changes. Each file's #include lines are cached in
<out.mk>.cache by size and mtime, so a run reads only what changed.
"""
import json
import os
import re
import sys

INCLUDE = re.compile(rb'^[ \t]*#[ \t]*include[ \t]*([<"])([^>"\r\n]+)[>"]', re.M)
RCINCLUDE = re.compile(rb'^[ \t]*rcinclude[ \t]+"?([^"\r\n]+?)"?[ \t]*$', re.M | re.I)
# a resource statement that names a file: `<name> <type> [<option>...] "<file>"`
RESFILE = re.compile(rb'^[ \t]*\w+[ \t]+\w+(?:[ \t]+(?:DISCARDABLE|PRELOAD|LOADONCALL|MOVEABLE'
                     rb'|FIXED|PURE|IMPURE|SHARED|NONSHARED))*[ \t]+"([^"\r\n]+)"[ \t]*(?://[^\r\n]*)?\r?$',
                     re.M | re.I)
CACHE_VERSION = 2


class Resolver:
    def __init__(self, cache):
        self.cache = cache          # path -> [size, mtime, [[kind, name], ...]]
        self.listings = {}          # dir -> {lowercase name: real name}
        self.seen = {}

    def listing(self, d):
        if d not in self.listings:
            try:
                self.listings[d] = {n.lower(): n for n in os.listdir(d)}
            except OSError:
                self.listings[d] = {}
        return self.listings[d]

    def find(self, base, name, isdir=False):
        """base/name, matched case-insensitively component by component."""
        p = base
        for part in name.replace("\\", "/").split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                p = os.path.dirname(p) if p not in ("", ".") else ".."
                if p == "":
                    p = "."
                continue
            real = self.listing(p).get(part.lower())
            if real is None:
                return None
            p = os.path.join(p, real)
        ok = os.path.isdir(p) if isdir else os.path.isfile(p)
        return os.path.normpath(p) if ok else None

    def includes(self, path):
        st = os.stat(path)
        c = self.cache.get(path)
        if c and c[0] == st.st_size and c[1] == st.st_mtime:
            return c[2]
        with open(path, "rb") as f:
            data = f.read()
        inc = [[k.decode(), n.decode("latin-1").strip()] for k, n in INCLUDE.findall(data)]
        inc += [['"', n.decode("latin-1").strip()] for n in RCINCLUDE.findall(data)]
        inc += [["r", n.decode("latin-1").strip()] for n in RESFILE.findall(data)]
        self.cache[path] = [st.st_size, st.st_mtime, inc]
        return inc

    def deps(self, source, dirs, rc=None):
        """What <source> includes; for a resource script, <rc> is the
        working directory, and the files its resources name count too."""
        out, todo = set(), [source]
        srcdir = os.path.dirname(source)
        while todo:
            f = todo.pop()
            for kind, name in self.includes(f):
                if kind == "r" and rc is None:
                    continue
                cands = ([os.path.dirname(f), srcdir] if kind != "<" else []) + ([rc] if rc else []) + dirs
                for d in cands:
                    hit = self.find(d, name)
                    if hit:
                        if hit not in out:
                            out.add(hit)
                            todo.append(hit)
                        break
        return sorted(out)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    spec, outmk = sys.argv[1:]
    cachefile = outmk + ".cache"
    try:
        with open(cachefile) as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    if cache.get("") != CACHE_VERSION:
        cache = {"": CACHE_VERSION}
    r = Resolver(cache)
    lines, headers = [], set()
    with open(spec) as f:
        for row in f:
            row = row.rstrip("\n")
            if not row:
                continue
            obj, cwd, source, args = row.split("\t")
            real = r.find(cwd, source)
            if real is None:
                continue        # generated: the Makefile names its inputs
            words, dl = args.split(), []
            for i, w in enumerate(words):
                if w.upper() == "/I" and i + 1 < len(words):
                    dl.append(words[i + 1])
                elif w.upper().startswith("/I") and len(w) > 2 and w[2] not in "fF":
                    dl.append(w[2:])
            dl = [r.find(cwd, d, isdir=True) for d in dl]
            isrc = real.lower().endswith(".rc")
            hs = r.deps(real, [d for d in dl if d] + ["src/nolf2src"], rc=os.path.normpath(cwd) if isrc else None)
            if isrc:
                # every file in the script's directory and in each /i one
                hs = sorted(set(hs).union(
                    os.path.normpath(os.path.join(d, n))
                    for d in {os.path.dirname(real)} | {d for d in dl if d}
                    for n in r.listing(d).values() if os.path.isfile(os.path.join(d, n))))
            headers.update(hs)
            lines.append(f"{obj}: {' '.join([real] + hs)}\n")
    lines += [f"{h}:\n" for h in sorted(headers)]
    text = "".join(lines)
    try:
        with open(outmk) as f:
            same = f.read() == text
    except OSError:
        same = False
    if not same:
        os.makedirs(os.path.dirname(outmk) or ".", exist_ok=True)
        with open(outmk + ".tmp", "w") as f:
            f.write(text)
        os.replace(outmk + ".tmp", outmk)
    with open(cachefile + ".tmp", "w") as f:
        json.dump(cache, f)
    os.replace(cachefile + ".tmp", cachefile)


if __name__ == "__main__":
    main()
