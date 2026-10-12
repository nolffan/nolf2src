"""A partial MSVC (VC6) name demangler, deliberately conservative.

Written for tools/asmweb.py, which labels a disassembly with the signatures of
the functions we have reconstructed. The mangled names are already in the
objects; this turns `?SendToObject@CLTServer@@QAEKAAVIMessageWrite@@KPAV
LTObject@@1K@Z` into something a person can read.

It covers what this codebase actually contains and REFUSES everything else:
any unknown code raises and `demangle` returns None, so the caller falls back
to the mangled string. That is the whole design rule -- a wrong signature is
worse than no signature, because the point of an annotation is that it can be
trusted. Coverage on server.dll is 1544 of 1545 placed symbols; the holdout
(`?quat_ConvertFromMatrix@@YAXPAMQAY03$$CBM@Z`) uses array types, which are
not implemented.

Three details cost real debugging and are worth keeping in mind if it is
extended:

  * MSVC never back-references a PRIMITIVE type, only compound ones. Counting
    primitives shifts every later index, and the symbol that exposes it is
    ?SendToObject@CLTServer@@QAEKAAVIMessageWrite@@KPAVLTObject@@1K@Z, whose
    `1` is the LTObject* and not the unsigned long between them.
  * A template instantiation occupies ONE name slot holding the whole
    `name<args>`; the bare base name must not also take one
    (?Cross@?$_CVector@M@@QBE?AV1@V1@@Z).
  * A constructor or destructor encodes its absent return type as a bare `@`,
    which still has to be consumed.

Usage:
  from msvcdemangle import demangle
  demangle(sym) -> readable signature, or None if it cannot be parsed safely
"""

PRIM = {
    "X": "void", "D": "char", "E": "unsigned char", "C": "signed char",
    "F": "short", "G": "unsigned short", "H": "int", "I": "unsigned int",
    "J": "long", "K": "unsigned long", "M": "float", "N": "double",
    "O": "long double", "_J": "__int64", "_K": "unsigned __int64",
    "_N": "bool", "_W": "wchar_t", "_D": "__int8", "_E": "unsigned __int8",
}
CV = {"A": "", "B": " const", "C": " volatile", "D": " const volatile"}
CALL = {"A": "__cdecl", "B": "__cdecl", "C": "__pascal", "E": "__thiscall",
        "G": "__stdcall", "I": "__fastcall"}
# access/kind -> (prefix, is_member, is_static)
KIND = {
    "A": ("private: ", 1, 0),        "B": ("private: ", 1, 0),
    "C": ("private: static ", 1, 1), "D": ("private: static ", 1, 1),
    "E": ("private: virtual ", 1, 0), "F": ("private: virtual ", 1, 0),
    "I": ("protected: ", 1, 0),      "J": ("protected: ", 1, 0),
    "K": ("protected: static ", 1, 1), "L": ("protected: static ", 1, 1),
    "M": ("protected: virtual ", 1, 0), "N": ("protected: virtual ", 1, 0),
    "Q": ("public: ", 1, 0),         "R": ("public: ", 1, 0),
    "S": ("public: static ", 1, 1),  "T": ("public: static ", 1, 1),
    "U": ("public: virtual ", 1, 0), "V": ("public: virtual ", 1, 0),
    "Y": ("", 0, 0), "Z": ("", 0, 0),
}
OPS = {
    "0": "#ctor", "1": "#dtor", "2": "operator new", "3": "operator delete",
    "4": "operator=", "5": "operator>>", "6": "operator<<", "7": "operator!",
    "8": "operator==", "9": "operator!=", "A": "operator[]",
    "B": "operator #cast", "C": "operator->", "D": "operator*",
    "E": "operator++", "F": "operator--", "G": "operator-", "H": "operator+",
    "I": "operator&", "J": "operator->*", "K": "operator/", "L": "operator%",
    "M": "operator<", "N": "operator<=", "O": "operator>", "P": "operator>=",
    "Q": "operator,", "R": "operator()", "S": "operator~", "T": "operator^",
    "U": "operator|", "V": "operator&&", "W": "operator||", "X": "operator*=",
    "Y": "operator+=", "Z": "operator-=",
    "_0": "operator/=", "_1": "operator%=", "_2": "operator>>=",
    "_3": "operator<<=", "_4": "operator&=", "_5": "operator|=",
    "_6": "operator^=", "_7": "`vftable'", "_8": "`vbtable'",
    "_9": "`vcall'", "_A": "`typeof'", "_B": "`local static guard'",
    "_E": "`vector deleting destructor'", "_G": "`scalar deleting destructor'",
    "_H": "`vector constructor iterator'",
    "_I": "`vector destructor iterator'",
}


class Fail(Exception):
    pass


class P:
    def __init__(self, s):
        self.s, self.i = s, 0
        self.names = []      # name backreference table (?0-?9)
        self.args = []       # argument-type backreference table

    def eof(self):
        return self.i >= len(self.s)

    def peek(self):
        if self.eof():
            raise Fail("eof")
        return self.s[self.i]

    def take(self):
        c = self.peek()
        self.i += 1
        return c

    def expect(self, c):
        if self.take() != c:
            raise Fail("expected " + c)

    # ---- names -----------------------------------------------------------
    def frag(self):
        """One '@'-terminated name fragment, or a backreference digit."""
        c = self.peek()
        if c.isdigit():
            self.take()
            k = int(c)
            if k >= len(self.names):
                raise Fail("bad name backref")
            return self.names[k]
        if c == "?":                      # a nested template or special name
            self.take()
            if self.peek() == "$":        # ?$name@... : a template instance
                self.take()
                # A template instantiation occupies ONE backreference slot,
                # holding the whole `name<args>`. The bare base name must not
                # also take one, or every later digit is off by one --
                # ?Cross@?$_CVector@M@@QBE?AV1@V1@@Z is the case that shows
                # it: its `V1@` is _CVector<float>, not _CVector.
                mark = len(self.names)
                base = self.frag()
                targs = []
                while self.peek() != "@":
                    targs.append(self.type())
                self.expect("@")
                out = "%s<%s>" % (base, ", ".join(targs))
                del self.names[mark:]
                self.names.append(out)
                return out
            raise Fail("nested special name")
        j = self.s.find("@", self.i)
        if j < 0:
            raise Fail("unterminated fragment")
        out = self.s[self.i:j]
        self.i = j + 1
        if not out:
            raise Fail("empty fragment")
        self.names.append(out)
        return out

    def scope(self):
        """Fragments up to the '@@' that closes the qualified name."""
        parts = []
        while True:
            if self.peek() == "@":         # the second '@' of '@@'
                self.take()
                return parts
            parts.append(self.frag())

    # ---- types -----------------------------------------------------------
    def type(self):
        self.prim = False
        c = self.take()
        if c == "?":               # `?A...`: a by-value return, cv-qualified
            q = self.take()
            if q not in CV:
                raise Fail("retcv " + q)
            t = self.type()
            self.prim = False
            return t + CV[q]
        if c == "_":
            k = "_" + self.take()
            if k not in PRIM:
                raise Fail("prim " + k)
            self.prim = True
            return PRIM[k]
        if c in PRIM:
            self.prim = True
            return PRIM[c]
        if c in "VUT":                     # class / struct / union
            kw = {"V": "class", "U": "struct", "T": "union"}[c]
            out = "%s %s" % (kw, self.qname())
            self.prim = False
            return out
        if c == "W":                       # enum
            self.take()                    # underlying-type digit
            out = "enum %s" % self.qname()
            self.prim = False
            return out
        if c in "PAQR":                    # pointer / reference
            if self.peek() == "6":         # pointer to function
                self.take()
                cv = self.take()           # calling convention
                if cv not in CALL:
                    raise Fail("fnptr cc")
                ret = self.type()
                args = self.arglist()
                sym = "*" if c in "PQ" else "&"
                out = "%s (%s %s)(%s)" % (ret, CALL[cv], sym, ", ".join(args))
                self.prim = False
                return out
            q = self.take()
            if q not in CV:
                raise Fail("cv " + q)
            inner = self.type()
            sym = "*" if c in "PQ" else "&"
            konst = " const" if c in "QS" else ""
            out = "%s%s %s%s" % (inner, CV[q], sym, konst)
            self.prim = False
            return out
        raise Fail("type " + c)

    def qname(self):
        parts = self.scope()
        return "::".join(reversed(parts))

    def arglist(self):
        """Argument types up to the terminating 'Z'."""
        if self.peek() == "X":             # (void)
            self.take()
            self.expect("Z")
            return []
        out = []
        while True:
            c = self.peek()
            if c == "@":
                self.take()
                self.expect("Z")
                return out
            if c == "Z":                   # varargs
                self.take()
                out.append("...")
                return out
            if c.isdigit():
                self.take()
                k = int(c)
                if k >= len(self.args):
                    raise Fail("bad arg backref")
                out.append(self.args[k])
                continue
            t = self.type()
            out.append(t)
            # Only COMPOUND types enter the backreference table -- MSVC never
            # back-references a primitive, and counting them shifts every
            # later index. ?SendToObject@CLTServer@@QAEKAAVIMessageWrite@@K
            # PAVLTObject@@1K@Z is the case that shows it: its `1` is the
            # LTObject*, not the unsigned long that sits between them.
            if not self.prim:
                self.args.append(t)


def demangle(sym):
    """Return a readable signature, or None if it cannot be parsed safely."""
    if not sym.startswith("?"):
        return sym[1:] if sym.startswith("_") and len(sym) > 1 else sym
    try:
        p = P(sym[1:])
        special = None
        if p.peek() == "?":                # ?? : an operator or special name
            p.take()
            c = p.take()
            key = ("_" + p.take()) if c == "_" else c
            if key not in OPS:
                raise Fail("op " + key)
            special = OPS[key]
            name = None
        elif p.peek() == "$":              # ?$... : a template function
            p.take()
            name = p.frag()
            targs = []
            while p.peek() != "@":
                targs.append(p.type())
            p.expect("@")
            name = "%s<%s>" % (name, ", ".join(targs))
        else:
            name = p.frag()

        scope = list(reversed(p.scope()))
        if special:                        # ctor/dtor take the class's name
            cls = scope[-1] if scope else ""
            base = cls.split("<")[0]
            name = ("%s" % base) if special == "#ctor" else \
                   ("~%s" % base) if special == "#dtor" else special
        full = "::".join(scope + [name]) if scope else name

        if p.eof():
            return full
        kind = p.take()
        if kind == "3":                    # static/global data
            t = p.type()
            p.take()                       # cv
            return "%s %s" % (t, full)
        if kind not in KIND:
            raise Fail("kind " + kind)
        pre, member, static = KIND[kind]
        thiscv = ""
        if member and not static:
            q = p.take()
            if q not in CV:
                raise Fail("thiscv " + q)
            thiscv = CV[q]
        cc = p.take()
        if cc not in CALL:
            raise Fail("cc " + cc)
        if special in ("#ctor", "#dtor"):
            p.expect("@")          # the placeholder where a return type goes
            ret = ""
        else:
            ret = p.type()
        args = p.arglist()
        head = "%s%s " % (pre, ret) if ret else pre
        return "%s%s %s(%s)%s" % (head, CALL[cc], full,
                                  ", ".join(args) or "void", thiscv)
    except (Fail, IndexError, ValueError):
        return None
