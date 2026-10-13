#!/usr/bin/env python3
"""Reader for the Mac NOLF2 engine: a Mach-O PowerPC image, not stripped.

The Mac release of NOLF2 (2003, rez's `nolf2-mac-usa`) is Mach-O for Mac OS X,
built with Apple's GCC 3.1. Its engine, NOLF2.app/Contents/MacOS/NOLF2, and the
dedicated server's engine, NOLF2Srv.app/Contents/Resources/server.dll/
Contents/MacOS/server, keep their symbol tables: every function of the engine
has its Itanium-mangled C++ name. This is the naming and inventory oracle for
the Windows engine's reconstruction (tools/macinventory.py builds the
inventory in progress/engine/ from it).

    tools/macho.py info  [file]            header, segments, sections, symbol counts
    tools/macho.py syms  [file] [regex]    every symbol: type, section, address, name
    tools/macho.py funcs [file] [regex]    functions with their extents, demangled
    tools/macho.py paths [file]            source-path strings and who references them
    tools/macho.py refs  [file] <0xaddr>   the addresses one function references
    tools/macho.py demangle <name>...      the demangler on its own

[file] is a path, or `engine` (the default) or `server`, which resolve under
rez/games/nolf2-mac-usa (`--root <dir>` or $NOLF2_MAC for another install).
Install it with `rez/fetch-isos.sh nolf2-mac-usa && rez/install-games.sh
nolf2-mac-usa` (the two USA Mac discs).

Plain Python 3, no dependencies. The demangler (`demangle()`) follows the
Itanium C++ ABI and prints what binutils' c++filt prints for every name in
these two binaries. A fat (universal) file is read for its PowerPC slice.
"""

import os
import re
import struct
import sys

ROOT_DEFAULT = "rez/games/nolf2-mac-usa"
KNOWN = {
    "engine": "NOLF2.app/Contents/MacOS/NOLF2",
    "server": "NOLF2Srv.app/Contents/Resources/server.dll/Contents/MacOS/server",
}

CPU_PPC = 18
N_STAB, N_TYPE, N_EXT = 0xe0, 0x0e, 0x01
N_UNDF, N_ABS, N_SECT, N_INDR = 0x0, 0x2, 0xe, 0xa
S_PURE_INSTR, S_SOME_INSTR = 0x80000000, 0x400
S_TYPE_MASK, S_SYMBOL_STUBS = 0xff, 0x8


def resolve(arg, root=None):
    """A file argument: a path, or `engine` / `server` under the Mac install."""
    if arg in KNOWN:
        root = root or os.environ.get("NOLF2_MAC") or ROOT_DEFAULT
        return os.path.join(root, KNOWN[arg])
    return arg


class Section:
    def __init__(self, index, seg, name, addr, size, offset, flags):
        self.index, self.seg, self.name = index, seg, name
        self.addr, self.size, self.offset, self.flags = addr, size, offset, flags

    @property
    def end(self):
        return self.addr + self.size

    @property
    def is_code(self):
        return bool(self.flags & (S_PURE_INSTR | S_SOME_INSTR)) and \
            (self.flags & S_TYPE_MASK) != S_SYMBOL_STUBS

    def __repr__(self):
        return "%s,%s" % (self.seg, self.name)


class Symbol:
    __slots__ = ("name", "type", "sect", "desc", "value")

    def __init__(self, name, typ, sect, desc, value):
        self.name, self.type, self.sect, self.desc, self.value = \
            name, typ, sect, desc, value

    @property
    def external(self):
        return bool(self.type & N_EXT)

    @property
    def defined(self):
        return not (self.type & N_STAB) and (self.type & N_TYPE) == N_SECT


class Function:
    __slots__ = ("addr", "size", "name", "aliases", "section", "external")

    def __init__(self, addr, size, name, aliases, section, external):
        self.addr, self.size, self.name = addr, size, name
        self.aliases, self.section, self.external = aliases, section, external


class MachO:
    def __init__(self, path):
        with open(path, "rb") as f:
            data = f.read()
        base = 0
        if data[:4] == b"\xca\xfe\xba\xbe":            # fat: take the PPC slice
            n = struct.unpack_from(">I", data, 4)[0]
            for i in range(n):
                cpu, _, off, size, _ = struct.unpack_from(">5I", data, 8 + 20 * i)
                if cpu == CPU_PPC:
                    data, base = data[off:off + size], off
                    break
            else:
                raise ValueError("%s: no PowerPC slice" % path)
        magic = data[:4]
        if magic != b"\xfe\xed\xfa\xce":
            raise ValueError("%s: not a 32-bit big-endian Mach-O" % path)
        self.path, self.data = path, data
        (_, self.cputype, self.cpusubtype, self.filetype, ncmds, _,
         self.flags) = struct.unpack_from(">7I", data, 0)
        self.segments, self.sections, self.dylibs = [], [], []
        symtab = None
        o = 28
        for _ in range(ncmds):
            cmd, size = struct.unpack_from(">II", data, o)
            if cmd == 0x1:                             # LC_SEGMENT
                seg = data[o + 8:o + 24].rstrip(b"\0").decode()
                vmaddr, vmsize, fileoff, filesize, _, _, nsects, _ = \
                    struct.unpack_from(">8I", data, o + 24)
                self.segments.append((seg, vmaddr, vmsize, fileoff, filesize))
                so = o + 56
                for _ in range(nsects):
                    sn = data[so:so + 16].rstrip(b"\0").decode()
                    sg = data[so + 16:so + 32].rstrip(b"\0").decode()
                    addr, ssize, off, _, _, _, flags = \
                        struct.unpack_from(">7I", data, so + 32)
                    self.sections.append(Section(len(self.sections) + 1, sg, sn,
                                                 addr, ssize, off, flags))
                    so += 68
            elif cmd == 0x2:                           # LC_SYMTAB
                symtab = struct.unpack_from(">4I", data, o + 8)
            elif cmd in (0xc, 0xd):                    # LC_LOAD_DYLIB / ID_DYLIB
                nameoff = struct.unpack_from(">I", data, o + 8)[0]
                nm = data[o + nameoff:o + size].split(b"\0")[0].decode()
                self.dylibs.append(("id " if cmd == 0xd else "") + nm)
            o += size
        self.symbols = []
        if symtab:
            symoff, nsyms, stroff, _ = symtab
            for i in range(nsyms):
                strx, typ, sect, desc, val = \
                    struct.unpack_from(">IBBhI", data, symoff + 12 * i)
                end = data.index(b"\0", stroff + strx)
                name = data[stroff + strx:end].decode("latin-1")
                self.symbols.append(Symbol(name, typ, sect, desc, val))

    # -- addresses -------------------------------------------------------
    def section(self, index_or_name):
        for s in self.sections:
            if s.index == index_or_name or s.name == index_or_name:
                return s
        return None

    def section_at(self, addr):
        for s in self.sections:
            if s.addr <= addr < s.end:
                return s
        return None

    def read(self, addr, size):
        s = self.section_at(addr)
        if s is None or s.offset == 0:              # zero-fill (bss, common)
            return None
        o = s.offset + addr - s.addr
        return self.data[o:o + size]

    def cstring(self, addr, limit=512):
        b = self.read(addr, limit)
        if b is None:
            return None
        return b.split(b"\0")[0].decode("latin-1")

    # -- functions -------------------------------------------------------
    def functions(self):
        """Every named function in a code section, with its extent: from its
        symbol to the next symbol of the same section, or the section end.
        Several names at one address are one function (aliases). Exception
        frame labels (`*.eh`) live in __eh_frame, not code, and are left out.
        __StaticInit, which has no symbols, contributes one function per
        __mod_init_func entry that points into it, named `<static init N>`."""
        code = {s.index: s for s in self.sections if s.is_code}
        by_addr = {}
        for sym in self.symbols:
            if not sym.defined or sym.sect not in code:
                continue
            by_addr.setdefault((sym.sect, sym.value), []).append(sym)
        init = self.section("__StaticInit")
        if init is not None:
            mif = self.section("__mod_init_func")
            if mif is not None:
                ptrs = struct.unpack_from(">%dI" % (mif.size // 4), self.data,
                                          mif.offset)
                for n, p in enumerate(ptrs):
                    if init.addr <= p < init.end and (init.index, p) not in by_addr:
                        by_addr[(init.index, p)] = [Symbol("<static init %d>" % n,
                                                           N_SECT, init.index, 0, p)]
        funcs = []
        for sidx, sec in sorted(code.items()):
            addrs = sorted(a for (s, a) in by_addr if s == sidx)
            for i, a in enumerate(addrs):
                end = addrs[i + 1] if i + 1 < len(addrs) else sec.end
                syms = by_addr[(sidx, a)]
                # prefer an external name, then a mangled one, then the shortest
                syms.sort(key=lambda s: (not s.external,
                                         not s.name.startswith("__Z"),
                                         len(s.name), s.name))
                funcs.append(Function(a, end - a, syms[0].name,
                                      [s.name for s in syms[1:]], sec.name,
                                      any(s.external for s in syms)))
        funcs.sort(key=lambda f: f.addr)
        return funcs

    # -- references (PowerPC) --------------------------------------------
    def refs(self, func):
        """Absolute addresses a function computes: `lis`/`addis` + `addi` or
        a D-form load/store, from 0 or from the PIC base Apple's GCC loads
        with `bcl 20,31,$+4; mflr rN`. Also the targets of `bl`. Returns
        [(insn address, target, kind)] with kind 'addr', 'load' or 'call'."""
        code = self.read(func.addr, func.size) or b""
        val, out, picbase = {}, [], None
        for i in range(0, len(code) - 3, 4):
            pc = func.addr + i
            w = struct.unpack_from(">I", code, i)[0]
            op = w >> 26
            rd, ra = (w >> 21) & 31, (w >> 16) & 31
            simm = w & 0xffff
            if simm & 0x8000:
                simm -= 0x10000
            if w == 0x429f0005:                         # bcl 20,31,$+4
                picbase = pc + 4
                continue
            if (w & 0xfc1fffff) == 0x7c0802a6:          # mflr rD
                if picbase == pc:
                    val[rd] = picbase
                else:
                    val.pop(rd, None)
                continue
            if op == 18:                                # b / bl
                if w & 1:
                    li = w & 0x03fffffc
                    if li & 0x02000000:
                        li -= 0x04000000
                    out.append((pc, (li if w & 2 else pc + li) & 0xffffffff, "call"))
                continue
            if op == 15:                                # addis / lis
                base = 0 if ra == 0 else val.get(ra)
                if base is None:
                    val.pop(rd, None)
                else:
                    val[rd] = (base + (simm << 16)) & 0xffffffff
                continue
            if op == 14:                                # addi / li / la
                if ra != 0 and ra in val:
                    t = (val[ra] + simm) & 0xffffffff
                    out.append((pc, t, "addr"))
                    val[rd] = t
                else:
                    val.pop(rd, None)
                continue
            if 32 <= op <= 55:                          # D-form loads, stores
                if ra != 0 and ra in val:
                    out.append((pc, (val[ra] + simm) & 0xffffffff, "load"))
                if op < 36 or 40 <= op < 44 or op in (46, 48, 49, 50, 51):
                    if op != 46:
                        val.pop(rd, None)
                continue
            if op == 31 or op == 21 or op == 24 or op == 25 or op == 28:
                # register-to-register forms: the destination is rA for
                # logical ops (ori, oris, andi., rlwinm, or), rD otherwise
                if op in (21, 24, 25, 28):
                    if op == 24 and rd in val and simm >= 0 and w & 0xffff == 0:
                        val[ra] = val[rd]                # nop-ish ori
                    else:
                        val.pop(ra, None)
                else:
                    xo = (w >> 1) & 0x3ff
                    if xo == 444 and rd == ((w >> 11) & 31) and rd in val:
                        val[ra] = val[rd]                # mr rA,rS
                    elif xo in (444, 28, 60, 124, 284, 316, 412, 476, 24, 536,
                                792, 824, 954, 922, 26):
                        val.pop(ra, None)
                    else:
                        val.pop(rd, None)
                continue
            if op in (7, 8, 12, 13):                    # mulli, subfic, addic
                val.pop(rd, None)
        return out

    def strings(self, pattern=None):
        """(address, text) of every NUL-terminated string in __cstring."""
        sec = self.section("__cstring")
        if sec is None:
            return []
        blob = self.data[sec.offset:sec.offset + sec.size]
        out, start = [], 0
        for part in blob.split(b"\0"):
            s = part.decode("latin-1")
            if s and (pattern is None or re.search(pattern, s)):
                out.append((sec.addr + start, s))
            start += len(part) + 1
        return out

    def source_paths(self):
        return self.strings(r"(?i)^[\w ./:\\-]*\w\.(cpp|c|h|hpp|mm?)$")


# ---------------------------------------------------------------------------
# Itanium C++ ABI demangler (what binutils' c++filt prints)

class _Fail(Exception):
    pass


_BUILTIN = {
    "v": "void", "w": "wchar_t", "b": "bool", "c": "char", "a": "signed char",
    "h": "unsigned char", "s": "short", "t": "unsigned short", "i": "int",
    "j": "unsigned int", "l": "long", "m": "unsigned long", "x": "long long",
    "y": "unsigned long long", "n": "__int128", "o": "unsigned __int128",
    "f": "float", "d": "double", "e": "long double", "g": "__float128",
    "z": "...",
}
_LITSUFFIX = {"j": "u", "l": "l", "m": "ul", "x": "ll", "y": "ull", "i": ""}
_OPS = {
    "nw": "new", "na": "new[]", "dl": "delete", "da": "delete[]", "ps": "+",
    "ng": "-", "ad": "&", "de": "*", "co": "~", "pl": "+", "mi": "-",
    "ml": "*", "dv": "/", "rm": "%", "an": "&", "or": "|", "eo": "^",
    "aS": "=", "pL": "+=", "mI": "-=", "mL": "*=", "dV": "/=", "rM": "%=",
    "aN": "&=", "oR": "|=", "eO": "^=", "ls": "<<", "rs": ">>", "lS": "<<=",
    "rS": ">>=", "eq": "==", "ne": "!=", "lt": "<", "gt": ">", "le": "<=",
    "ge": ">=", "nt": "!", "aa": "&&", "oo": "||", "pp": "++", "mm": "--",
    "cm": ",", "pm": "->*", "pt": "->", "cl": "()", "ix": "[]", "qu": "?",
    "st": "sizeof ", "sz": "sizeof ", "at": "alignof ", "az": "alignof ",
}
_STD_SUBS = {
    "t": ("std", "std"),
    "a": ("std::allocator", "std::allocator"),
    "b": ("std::basic_string", "std::basic_string"),
    "s": ("std::string",
          "std::basic_string<char, std::char_traits<char>, std::allocator<char> >",
          "basic_string"),
    "i": ("std::istream",
          "std::basic_istream<char, std::char_traits<char> >", "basic_istream"),
    "o": ("std::ostream",
          "std::basic_ostream<char, std::char_traits<char> >", "basic_ostream"),
    "d": ("std::iostream",
          "std::basic_iostream<char, std::char_traits<char> >", "basic_iostream"),
}


# Type nodes: tuples. ("name", str) | ("builtin", str) | ("ptr", t) |
# ("ref", t) | ("cv", t, quals) | ("func", ret, [params], quals) |
# ("array", dim, t) | ("memptr", cls, t)

def _tstr(t):
    return _decl(t, "")


def _decl(t, inner):
    """Print type t around the declarator `inner`, as c++filt does:
    `int const*`, `void (*)(int)`, `int (*) [4]`, `void (Foo::*)() const`."""
    k = t[0]
    if k in ("name", "builtin"):
        if not inner or inner[0] in "*&":
            return t[1] + inner
        return t[1] + " " + inner
    if k == "cv":
        q = t[2]
        if not inner or inner[0] in "*&":
            return _decl(t[1], q + inner)
        return _decl(t[1], q + " " + inner)
    if k in ("ptr", "ref"):
        sym = "*" if k == "ptr" else "&"
        if inner and inner[0] not in "*&)":
            inner = " " + inner
        base = t[1]
        if base[0] == "cv" and base[1][0] == "array":   # const applies to elements
            base = ("array", base[1][1], ("cv", base[1][2], base[2]))
        if base[0] in ("func", "array"):
            return _decl(base, "(" + sym + inner + ")")
        return _decl(base, sym + inner)
    if k == "memptr":
        cls = _tstr(t[1])
        if inner and inner[0] not in "*&)":
            inner = " " + inner
        if t[2][0] == "func":
            return _decl(t[2], "(" + cls + "::*" + inner + ")")
        return _decl(t[2], cls + "::*" + inner)
    if k == "func":
        params = ", ".join(_tstr(p) for p in t[2])
        return _decl(t[1], inner + "(" + params + ")" + t[3])
    if k == "array":
        return _decl(t[2], (inner + " " if inner else "") + "[" + t[1] + "]")
    raise _Fail("type " + k)


class _Demangler:
    def __init__(self, s):
        self.s, self.i = s, 0
        self.subs = []
        self.tparams = []
        self.depth = 0      # > 0 while inside a type: its template args are
                            # not the encoding's template parameters

    def peek(self, n=1):
        return self.s[self.i:self.i + n]

    def eat(self, x):
        if self.s.startswith(x, self.i):
            self.i += len(x)
            return True
        return False

    def need(self, x):
        if not self.eat(x):
            raise _Fail("expected %r at %d" % (x, self.i))

    def number(self):
        neg = self.eat("n")
        j = self.i
        while self.i < len(self.s) and self.s[self.i].isdigit():
            self.i += 1
        if j == self.i:
            raise _Fail("number")
        n = int(self.s[j:self.i])
        return -n if neg else n

    def seq_id(self):
        if self.eat("_"):
            return 0
        j = self.i
        while self.i < len(self.s) and (self.s[self.i].isdigit() or self.s[self.i].isupper()):
            self.i += 1
        n = int(self.s[j:self.i], 36)
        self.need("_")
        return n + 1

    # -- top level -------------------------------------------------------
    def mangled(self):
        self.need("_Z")
        r = self.encoding(top=True)
        if self.i != len(self.s):
            rest = self.s[self.i:]
            m = re.match(r"^(\.[A-Za-z_]\w*)+$", rest)
            if not m:
                raise _Fail("trailing " + rest)
            for part in rest[1:].split("."):
                r += " [clone .%s]" % part
            self.i = len(self.s)
        return r

    def encoding(self, top=False):
        c = self.peek()
        if c in ("T", "G") and self.peek(2) not in ("",):
            sp = self.special()
            if sp is not None:
                return sp
        name, info = self.name()
        if self.i >= len(self.s) or self.peek() in ("E", "."):
            return name
        # bare function type
        ret = None
        if info["template"] and not info["ctor"] and not info["conv"]:
            ret = self.type()
        params = []
        while self.i < len(self.s) and self.peek() not in ("E", "."):
            params.append(self.type())
        if len(params) == 1 and params[0] == ("builtin", "void"):
            params = []
        ps = "(" + ", ".join(_tstr(p) for p in params) + ")" + info["quals"]
        if ret is not None:
            return _tstr(ret) + " " + name + ps
        return name + ps

    def special(self):
        if self.eat("TV"):
            return "vtable for " + _tstr(self.type())
        if self.eat("TT"):
            return "VTT for " + _tstr(self.type())
        if self.eat("TI"):
            return "typeinfo for " + _tstr(self.type())
        if self.eat("TS"):
            return "typeinfo name for " + _tstr(self.type())
        if self.eat("TF"):
            return "typeinfo fn for " + _tstr(self.type())
        if self.eat("Th"):
            self.number()
            self.need("_")
            return "non-virtual thunk to " + self.encoding()
        if self.eat("Tv"):
            self.number()
            self.need("_")
            self.number()
            self.need("_")
            return "virtual thunk to " + self.encoding()
        if self.eat("Tc"):
            for _ in range(2):
                self.call_offset()
            return "covariant return thunk to " + self.encoding()
        if self.eat("TC"):
            a = self.type()
            self.number()
            self.need("_")
            b = self.type()
            return "construction vtable for %s-in-%s" % (_tstr(b), _tstr(a))
        if self.eat("GV"):
            return "guard variable for " + self.name()[0]
        if self.eat("GR"):
            return "reference temporary for " + self.name()[0]
        return None

    def call_offset(self):
        if self.eat("h"):
            self.number()
            self.need("_")
        elif self.eat("v"):
            self.number()
            self.need("_")
            self.number()
            self.need("_")
        else:
            raise _Fail("call offset")

    # -- names -----------------------------------------------------------
    def name(self):
        """Returns (text, info) with info: template (ends in template
        args), ctor (ctor/dtor), conv (conversion operator), quals."""
        info = dict(template=False, ctor=False, conv=False, quals="")
        c = self.peek()
        if c == "N":
            return self.nested(info), info
        if c == "Z":
            return self.local(info), info
        if c == "S" and self.peek(2) != "St":
            # a substitution that is a template name, then args
            text, _ = self.substitution()
            if self.peek() != "I":
                raise _Fail("bare substitution as name")
            args = self.template_args(set_params=True)
            info["template"] = True
            return text + args, info
        std = self.eat("St")
        text, kind = self.unqualified(None)
        if std:
            text = "std::" + text
        if kind == "conv":
            info["conv"] = True
        if self.peek() == "I":
            self.subs.append(("name", text))
            text += self.template_args(set_params=True)
            info["template"] = True
        return text, info

    def local(self, info):
        self.need("Z")
        enc = self.encoding()
        self.need("E")
        if self.eat("s"):
            self.discriminator()
            return enc + "::string literal"
        sub, sinfo = self.name()
        info.update(sinfo)
        self.discriminator()
        return enc + "::" + sub

    def discriminator(self):
        if self.eat("_"):
            if self.eat("_"):
                self.number()
                self.need("_")
            else:
                self.number()

    def nested(self, info):
        self.need("N")
        quals = ""
        while self.peek() in ("r", "V", "K"):
            q = self.s[self.i]
            self.i += 1
            quals = {"r": " restrict", "V": " volatile", "K": " const"}[q] + quals
        # order: const volatile restrict as c++filt prints them
        qs = []
        if "const" in quals:
            qs.append("const")
        if "volatile" in quals:
            qs.append("volatile")
        if "restrict" in quals:
            qs.append("restrict")
        info["quals"] = "".join(" " + q for q in qs)
        parts = []          # printed components
        last = None         # last unqualified name (for ctor/dtor)
        while True:
            c = self.peek()
            if c == "E":
                self.i += 1
                break
            if c == "S" and not parts:
                if self.peek(2) == "St":
                    self.i += 2
                    parts.append("std")
                    continue
                text, ctorname = self.substitution(prefix=True)
                parts.append(text)
                last = ctorname
                info["template"] = False
                continue
            if c == "I":
                if not parts:
                    raise _Fail("template args first")
                args = self.template_args(set_params=True)
                parts[-1] += args
                info["template"] = True
                if self.peek() != "E":
                    self.subs.append(("name", "::".join(parts)))
                continue
            if c == "T":
                t = self.template_param()
                parts.append(_tstr(t))
                last = _tstr(t)
                info["template"] = False
                if self.peek() != "E":
                    self.subs.append(("name", "::".join(parts)))
                continue
            text, kind = self.unqualified(last)
            info["ctor"] = kind == "ctor"
            info["conv"] = kind == "conv"
            info["template"] = False
            if kind == "plain":
                last = text
            parts.append(text)
            if self.peek() != "E":
                self.subs.append(("name", "::".join(parts)))
        return "::".join(parts)

    def unqualified(self, last):
        c = self.peek()
        if c.isdigit():
            n = self.number()
            ident = self.s[self.i:self.i + n]
            if len(ident) != n:
                raise _Fail("short identifier")
            self.i += n
            if ident.startswith("_GLOBAL_") and len(ident) > 9 and ident[8] in "._$" \
                    and ident[9] == "N":
                return "(anonymous namespace)", "plain"
            return ident, "plain"
        if c in ("C", "D") and self.peek(2)[1:2].isdigit():
            self.i += 2
            if last is None:
                raise _Fail("ctor without class")
            base = re.sub(r"<.*$", "", last)
            base = base.rsplit("::", 1)[-1]
            return ("~" if c == "D" else "") + base, "ctor"
        if self.eat("cv"):
            t = self.type()
            return "operator " + _tstr(t), "conv"
        two = self.peek(2)
        if two in _OPS:
            self.i += 2
            op = _OPS[two]
            sep = " " if op[0].isalpha() else ""
            return "operator" + sep + op, "op"
        if c == "v" and self.peek(2)[1:2].isdigit():
            self.i += 2
            text, _ = self.unqualified(last)
            return "operator " + text, "op"
        raise _Fail("unqualified name at %d" % self.i)

    def substitution(self, prefix=False):
        """S_, S<n>_ or St/Sa/Sb/Ss/Si/So/Sd. Returns (text, ctor name)."""
        self.need("S")
        c = self.peek()
        if c and c.islower():
            self.i += 1
            if c not in _STD_SUBS:
                raise _Fail("std sub " + c)
            e = _STD_SUBS[c]
            nxt = self.peek()
            # c++filt is verbose: the full expansion, always
            if len(e) == 3:
                return e[1], e[2]
            return e[0], e[0].rsplit("::", 1)[-1]
        n = self.seq_id()
        if n >= len(self.subs):
            raise _Fail("substitution %d" % n)
        kind, val = self.subs[n]
        text = val if kind == "name" else _tstr(val)
        last = re.sub(r"<.*$", "", text).rsplit("::", 1)[-1]
        return text, last

    def template_args(self, set_params=False):
        self.need("I")
        args = []
        while not self.eat("E"):
            args.append(self.template_arg())
        if set_params and self.depth == 0:
            self.tparams = args
        s = "<" + ", ".join(a if isinstance(a, str) else _tstr(a) for a in args)
        if s.endswith(">"):
            s += " "
        return s + ">"

    def template_arg(self):
        c = self.peek()
        if c == "L":
            return self.literal()
        if c == "X":
            raise _Fail("expression")
        return self.type()

    def literal(self):
        self.need("L")
        if self.eat("_Z"):
            r = self.encoding()
            self.need("E")
            return r
        t = self.type()
        j = self.i
        while self.peek() != "E":
            self.i += 1
        v = self.s[j:self.i]
        self.need("E")
        neg = v.startswith("n")
        if neg:
            v = "-" + v[1:]
        tn = t[1] if t[0] == "builtin" else None
        code = {b: a for a, b in _BUILTIN.items()}.get(tn)
        if code == "b":
            return {"0": "false", "1": "true"}.get(v, "(bool)" + v)
        if code in _LITSUFFIX:
            return v + _LITSUFFIX[code]
        return "(" + _tstr(t) + ")" + v

    def template_param(self):
        self.need("T")
        n = 0 if self.eat("_") else None
        if n is None:
            n = self.number() + 1
            self.need("_")
        if n >= len(self.tparams):
            raise _Fail("template param %d" % n)
        a = self.tparams[n]
        return a if not isinstance(a, str) else ("name", a)

    # -- types -----------------------------------------------------------
    def type(self):
        self.depth += 1
        try:
            return self._type()
        finally:
            self.depth -= 1

    def _type(self):
        c = self.peek()
        if c in _BUILTIN:
            self.i += 1
            return ("builtin", _BUILTIN[c])
        if c == "u":
            self.i += 1
            n = self.number()
            t = ("name", self.s[self.i:self.i + n])
            self.i += n
            self.subs.append(("type", t))
            return t
        if c in ("r", "V", "K"):
            qs = []
            while self.peek() in ("r", "V", "K"):
                qs.append(self.s[self.i])
                self.i += 1
            base = self.type()
            words = [w for q, w in (("K", "const"), ("V", "volatile"),
                                    ("r", "restrict")) if q in qs]
            t = ("cv", base, " ".join(words))
            self.subs.append(("type", t))
            return t
        if c in ("P", "R", "O"):
            self.i += 1
            base = self.type()
            t = ("ptr" if c == "P" else "ref", base)
            self.subs.append(("type", t))
            return t
        if c == "F":
            self.i += 1
            self.eat("Y")
            ret = self.type()
            params = []
            while not self.eat("E"):
                params.append(self.type())
            if len(params) == 1 and params[0] == ("builtin", "void"):
                params = []
            t = ("func", ret, params, "")
            self.subs.append(("type", t))
            return t
        if c == "A":
            self.i += 1
            dim = ""
            if self.peek().isdigit():
                dim = str(self.number())
            self.need("_")
            t = ("array", dim, self.type())
            self.subs.append(("type", t))
            return t
        if c == "M":
            self.i += 1
            cls = self.type()
            mem = self.type()
            if mem[0] == "cv" and mem[1][0] == "func":
                f = mem[1]
                mem = ("func", f[1], f[2], " " + mem[2])
            t = ("memptr", cls, mem)
            self.subs.append(("type", t))
            return t
        if c == "T":
            t = self.template_param()
            self.subs.append(("type", t))
            if self.peek() == "I":
                args = self.template_args()
                t = ("name", _tstr(t) + args)
                self.subs.append(("type", t))
            return t
        if c == "S":
            if self.peek(2) == "St":
                name, _ = self.name()
                t = ("name", name)
                self.subs.append(("type", t))
                return t
            j = self.i
            text, _ = self.substitution()
            std_abbrev = self.s[j + 1].islower()
            if self.peek() == "I":
                args = self.template_args()
                t = ("name", text + args)
                self.subs.append(("type", t))
                return t
            if not std_abbrev:
                kind_val = self.subs[self._last_seq(j)]
                if kind_val[0] == "type":
                    return kind_val[1]
            return ("name", text)
        if c == "D":
            two = self.peek(2)
            if two == "Dn":
                self.i += 2
                return ("builtin", "decltype(nullptr)")
            raise _Fail("D type")
        if c in ("N", "Z") or c.isdigit():
            name, _ = self.name()
            t = ("name", name)
            self.subs.append(("type", t))
            return t
        raise _Fail("type %r at %d" % (c, self.i))

    def _last_seq(self, j):
        s = self.s[j + 1:]
        if s.startswith("_"):
            return 0
        m = re.match(r"([0-9A-Z]+)_", s)
        return int(m.group(1), 36) + 1


def demangle(sym):
    """The demangled form of a (Mach-O, underscore-prefixed or not) Itanium
    name; the name itself when it is not mangled or not understood."""
    s = sym[1:] if sym.startswith("__Z") else sym
    if not s.startswith("_Z"):
        return sym
    try:
        return _Demangler(s).mangled()
    except (_Fail, IndexError, ValueError, KeyError):
        return sym


# ---------------------------------------------------------------------------

def _hex(x):
    return "0x%08x" % x


def cmd_info(m):
    print("file      %s" % m.path)
    print("cpu       %d/%d  filetype %d  flags 0x%x" % (m.cputype, m.cpusubtype,
                                                       m.filetype, m.flags))
    for d in m.dylibs:
        print("dylib     %s" % d)
    for seg in m.segments:
        print("segment   %-12s %s +0x%x  file 0x%x +0x%x" % (seg[0], _hex(seg[1]),
                                                            seg[2], seg[3], seg[4]))
    counts = {}
    for s in m.symbols:
        if s.defined:
            counts[s.sect] = counts.get(s.sect, 0) + 1
    for s in m.sections:
        print("  %2d %-8s %-18s %s +0x%-7x %s %5d syms" % (
            s.index, s.seg, s.name, _hex(s.addr), s.size,
            "code" if s.is_code else "    ", counts.get(s.index, 0)))
    f = m.functions()
    print("symbols   %d; functions %d (%d bytes)" % (len(m.symbols), len(f),
                                                     sum(x.size for x in f)))


def cmd_syms(m, pat):
    rx = re.compile(pat) if pat else None
    for s in m.symbols:
        d = demangle(s.name)
        if rx and not (rx.search(s.name) or rx.search(d)):
            continue
        print("%02x\t%d\t%s\t%s" % (s.type, s.sect, _hex(s.value), d))


def cmd_funcs(m, pat):
    rx = re.compile(pat) if pat else None
    for f in m.functions():
        d = demangle(f.name)
        if rx and not (rx.search(f.name) or rx.search(d)):
            continue
        print("%s\t%6d\t%-14s\t%s" % (_hex(f.addr), f.size, f.section, d))


def cmd_paths(m):
    paths = dict(m.source_paths())
    users = {a: [] for a in paths}
    for f in m.functions():
        for _, t, k in m.refs(f):
            if t in users and k != "call":
                users[t].append(demangle(f.name))
    for a, s in sorted(paths.items(), key=lambda x: x[1]):
        print("%s\t%s" % (_hex(a), s))
        for u in sorted(set(users[a])):
            print("\t\t%s" % u)


def cmd_refs(m, addr):
    fs = [f for f in m.functions() if f.addr <= addr < f.addr + f.size]
    if not fs:
        sys.exit("no function at %s" % _hex(addr))
    names = {f.addr: demangle(f.name) for f in m.functions()}
    for pc, t, k in m.refs(fs[0]):
        s = names.get(t)
        if s is None:
            sec = m.section_at(t)
            s = repr(m.cstring(t)) if sec is not None and sec.name == "__cstring" \
                else (str(sec) if sec else "")
        print("%s\t%-4s\t%s\t%s" % (_hex(pc), k, _hex(t), s))


def main(argv):
    root = None
    if "--root" in argv:
        k = argv.index("--root")
        root = argv[k + 1]
        del argv[k:k + 2]
    if not argv:
        sys.exit(__doc__)
    cmd, rest = argv[0], argv[1:]
    if cmd == "demangle":
        for n in rest:
            print(demangle(n))
        return
    path = "engine"
    if rest and (rest[0] in KNOWN or os.path.exists(rest[0])):
        path = rest.pop(0)
    m = MachO(resolve(path, root))
    if cmd == "info":
        cmd_info(m)
    elif cmd == "syms":
        cmd_syms(m, rest[0] if rest else None)
    elif cmd == "funcs":
        cmd_funcs(m, rest[0] if rest else None)
    elif cmd == "paths":
        cmd_paths(m)
    elif cmd == "refs":
        cmd_refs(m, int(rest[0], 0))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
