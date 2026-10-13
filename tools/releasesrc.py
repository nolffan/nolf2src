#!/usr/bin/env python3
"""The source the release build compiles: src/ without the variant blocks.

The debug and modern builds (build/variant.sh) add code to retail files in
`#ifdef NOLF2SRC_MODERN` / `#ifdef NOLF2SRC_DEBUG` blocks. The release build
never defines either, but a block it skips is still there: its lines move
everything below them, and VC6 lets that layout decide where it puts some
out-of-line inline functions. Enough blocks in one file can change the
release binary although not one release token changed.

So the release build does not compile src/ itself. build/compile.sh,
started in a checkout, runs in
out/release-tree/ instead (build/env.sh, nolf2src_release_tree): a copy of
src/ in which every such block is resolved as the release build sees it --
`#ifdef NOLF2SRC_X ... [#else ...] #endif` keeps only the #else part,
`#ifndef NOLF2SRC_X ... [#else ...] #endif` only the first -- with the
directives themselves gone. A retail file then reads exactly as it did
before anything was added to it, provided nothing was added OUTSIDE a block
(not even a blank line); `diff` shows what a change does to the release
build's input.

  tools/releasesrc.py strip <file>                 the file as the release build compiles it
  tools/releasesrc.py sync <src> <mirror-src>      bring the mirror up to date
  tools/releasesrc.py mirror <src> <copy-src>      the same, unstripped: a variant tree's
                                                   copy (build/variant.sh)
  tools/releasesrc.py outputs <from-src> <to-src>  make <to>'s build outputs match <from>'s
  tools/releasesrc.py diff [rev]                   release-visible changes to src/ since
                                                   <rev> (default HEAD), as a unified diff

Only NOLF2SRC_MODERN and NOLF2SRC_DEBUG are resolved, and only in the
`#ifdef`/`#ifndef` forms; any other test of them (#if, #elif, defined())
is an error, so the release build cannot silently compile the wrong side.
"""
import difflib
import os
import re
import shutil
import subprocess
import sys

VARIANT = ("NOLF2SRC_MODERN", "NOLF2SRC_DEBUG")
STRIP_EXT = (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh", ".inl",
             ".rc", ".rc2", ".asm", ".def", ".idl")
# build outputs: never mirrored as sources, synced by `outputs` -- anything
# in a built/ directory, where Monolith's project files put every output
# (Game/built/, libs/built/; spelled Built and built alike) -- and see
# GENERATED below
OUTPUT_DIRS = ("built",)

DIRECTIVE = re.compile(r"^\s*#\s*(ifdef|ifndef|if|elif|else|endif)\b(.*)$")


class StripError(Exception):
    pass


def in_comment_after(line, in_comment):
    """Whether a /* */ comment is still open after this line, given whether
    one was open before it (string and character literals and // comments
    are skipped). A directive on a line that starts inside a comment is no
    directive: retail files keep commented-out #if/#else/#endif blocks."""
    i, n = 0, len(line)
    while i < n:
        if in_comment:
            j = line.find("*/", i)
            if j < 0:
                return True
            in_comment, i = False, j + 2
            continue
        c = line[i]
        if c in "\"'":
            i += 1
            while i < n and line[i] != c:
                i += 2 if line[i] == "\\" else 1
            i += 1
        elif line.startswith("//", i):
            return False
        elif line.startswith("/*", i):
            in_comment, i = True, i + 2
        else:
            i += 1
    return in_comment


def strip_text(text, name="<text>"):
    """Resolve the variant conditionals as the release build sees them."""
    if not any(v in text for v in VARIANT):
        return text
    nl = "\r\n" if "\r\n" in text else "\n"
    out = []
    # one entry per open conditional: None for one we leave alone, else
    # [keep_now] for a variant block (its directives are dropped)
    stack = []
    in_comment = False
    for n, line in enumerate(text.split(nl), 1):
        m = None if in_comment else DIRECTIVE.match(line)
        in_comment = in_comment_after(line, in_comment)
        keep = all(s is None or s[0] for s in stack)
        if m:
            d, rest = m.group(1), m.group(2)
            word = rest.split("//")[0].split("/*")[0].strip()
            if d in ("ifdef", "ifndef") and word in VARIANT:
                # the release build defines neither
                stack.append([d == "ifndef"])
                continue
            if d in ("if", "elif") and any(v in rest for v in VARIANT):
                raise StripError(f"{name}:{n}: only #ifdef/#ifndef may test {'/'.join(VARIANT)}")
            if d in ("if", "ifdef", "ifndef"):
                stack.append(None)
            elif d == "elif":
                if stack and stack[-1] is not None:
                    raise StripError(f"{name}:{n}: #elif in a {'/'.join(VARIANT)} block")
            elif d == "else":
                if stack and stack[-1] is not None:
                    stack[-1][0] = not stack[-1][0]
                    continue
            elif d == "endif":
                if not stack:
                    raise StripError(f"{name}:{n}: #endif without #if")
                if stack.pop() is not None:
                    continue
        if keep:
            out.append(line)
    if any(s is not None for s in stack):
        raise StripError(f"{name}: unterminated {'/'.join(VARIANT)} block")
    return nl.join(out)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def stripped_bytes(path, data=None):
    data = read(path) if data is None else data
    if not path.lower().endswith(STRIP_EXT):
        return data
    text = data.decode("latin-1")
    return strip_text(text, path).encode("latin-1")


# files the build writes outside those directories (build/build.mk): the
# generated link inputs, flex's and bison's output, CRes.dll's top resource
# script
# the custom build steps' outputs, written beside their sources
GENERATED = re.compile(r"^Game/ObjectDLL/ObjectShared/(AnimationLex\.o|AnimationParse\.o|AnimationLexSymbols\.h)$",
                       re.I)


def is_output(rel):
    parts = rel.split(os.sep)
    if any(p.lower() in OUTPUT_DIRS for p in parts[:-1]):
        return True
    return bool(GENERATED.match("/".join(parts)))


def walk(root, outputs):
    """Relative paths of the files under root: sources, or build outputs."""
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), root)
            if is_output(rel) == outputs:
                yield rel


def write_if_changed(path, data):
    try:
        if read(path) == data:
            return False
    except FileNotFoundError:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return True


def cmd_sync(src, dst, strip=True):
    """Make dst's sources those of src (stripped, for the release tree),
    writing only the files that differ -- the rest keep their times, so the
    build in dst redoes only what changed -- and leaving dst's build outputs
    alone."""
    seen, changed = set(), 0
    for rel in walk(src, outputs=False):
        seen.add(rel)
        try:
            path = os.path.join(src, rel)
            data = stripped_bytes(path) if strip else read(path)
        except StripError as e:
            sys.exit(f"releasesrc: {e}")
        changed += write_if_changed(os.path.join(dst, rel), data)
    if os.path.isdir(dst):
        for rel in list(walk(dst, outputs=False)):
            if rel not in seen:
                os.remove(os.path.join(dst, rel))
    return changed


def cmd_outputs(src, dst):
    """Make dst's build outputs (built/, the generated sources) the same as
    src's: copy what differs (size or mtime, mtime kept), delete what src
    does not have."""
    have = set()
    for rel in walk(src, outputs=True):
        have.add(rel)
        a, b = os.path.join(src, rel), os.path.join(dst, rel)
        sa = os.stat(a)
        try:
            sb = os.stat(b)
            if sb.st_size == sa.st_size and int(sb.st_mtime) == int(sa.st_mtime):
                continue
        except FileNotFoundError:
            os.makedirs(os.path.dirname(b), exist_ok=True)
        shutil.copy2(a, b)
    if os.path.isdir(dst):
        for rel in list(walk(dst, outputs=True)):
            if rel not in have:
                os.remove(os.path.join(dst, rel))


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def cmd_diff(rev):
    files = git("ls-files", "-z", "src").decode().split("\0")
    old_files = set(git("ls-tree", "-r", "-z", "--name-only", rev, "src").decode().split("\0"))
    out = []
    for f in sorted(set(files) | old_files):
        if not f or not f.lower().endswith(STRIP_EXT) or f.startswith("src/modern/"):
            continue
        try:
            new = stripped_bytes(f) if os.path.exists(f) else b""
            old = stripped_bytes(f, git("show", f"{rev}:{f}")) if f in old_files else b""
        except StripError as e:
            sys.exit(f"releasesrc: {e}")
        if new != old:
            a = old.decode("latin-1").replace("\r\n", "\n").split("\n")
            b = new.decode("latin-1").replace("\r\n", "\n").split("\n")
            out += difflib.unified_diff(a, b, f"a/{f}", f"b/{f}", lineterm="")
    sys.stdout.write("".join(l + "\n" for l in out))
    return 1 if out else 0


def main():
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "strip":
        try:
            sys.stdout.buffer.write(stripped_bytes(a[1]))
        except StripError as e:
            sys.exit(f"releasesrc: {e}")
    elif len(a) == 3 and a[0] == "sync":
        n = cmd_sync(a[1], a[2])
        if n:
            print(f"   release tree: {n} source file(s) updated")
    elif len(a) == 3 and a[0] == "mirror":
        cmd_sync(a[1], a[2], strip=False)
    elif len(a) == 3 and a[0] == "outputs":
        cmd_outputs(a[1], a[2])
    elif a and a[0] == "diff" and len(a) <= 2:
        sys.exit(cmd_diff(a[1] if len(a) == 2 else "HEAD"))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
