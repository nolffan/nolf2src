# 03 · Reading VC6 disassembly back into C++

This is the reference you'll return to most. Given a block of shipped
disassembly, the job is to find the C++ that VC6 compiles to those exact bytes.
These idioms are the dictionary. They were learned by byte-matching
thousands of functions across NOLF1's libraries, launcher and engine, and
NOLF2's game DLLs; each is a pattern you'll see over and over. (Function
names below are NOLF1's engine where not said otherwise; the codegen is the
same VC6.)

A rule of thumb: **the compiler is deterministic.** The same source under the
same flags always produces the same bytes. So when your output differs, there
is a specific source difference to find — not luck to chase.

> **First, check the optimization level.** The game DLLs, the launcher and
> `Lithtech.exe` are `/O2`; **`server.dll` is `/O1`** (or `/Os`), as NOLF1's
> was (see the table in the [guides README](README.md#picking-a-target)).
> A wrong level makes *every* function in a binary nearly-but-not-quite right.
> See [the `/O1` tells](#o1-minimize-size-idioms) below.

---

## Control flow

**Duplicated `return`/epilogue blocks** → separate `if (...) return X;`
statements, each with its own exit.
**One shared epilogue** reached by several branches → conditions OR-merged into
one `if`, or nested ifs funnelling to a single `return`.

```asm
; three separate guards, each returns:
test eax,eax │ je L_ret0 ... test ecx,ecx │ je L_ret0   ; ← if(!a) return 0; if(!b) return 0;
; vs one merged test funnelling to a shared return:
                                                          ; ← if(!a || !b) return 0;
```

**A jump table (`jmp *TABLE(,%eax,4)`)** → a dense `switch`. VC6 builds a table
only when cases are dense and numerous; a sparse or few-case `switch` becomes a
linear `cmp/je` chain. To force the chain (matching shipped), write explicit
`if/else if` on the raw value in the shipped comparison order — the order is
visible in the disassembly and is *not* always sorted.

**`switch (uMsg)`** on a window/dialog proc compiles to a binary-search tree of
`cmp/ja/je` (e.g. `cmp 0x200; ja …; je …`). Reproduce it as a real `switch` on
`uMsg` with the same case values; the compiler rebuilds the tree.

**Loop shape:** a `for`/`while` with the test at the top emits the test, body,
and a back-edge. VC6 often rotates loops (jump to the test at the bottom).
Match the source loop form (`for` vs `while` vs `do`) to the branch structure,
not by feel — a `do/while` has no top test.

---

## Comparisons and booleans

**`jl`/`jge` (signed) vs `jb`/`jae` (unsigned)** tells you the operand types.
A signed branch where you emitted unsigned means a stray `(int)` cast (or vice
versa). Mixed `int`/`unsigned` comparisons promote to unsigned — the `C4018`
warning that produces is original, not a mistake to "fix".

**`x != 0` → `neg; sbb eax,eax; ...`** or **`xor eax,eax; test; setne al`**
(context-dependent).
**`x == 1` (i.e. `== BST_CHECKED`) → `dec; neg; sbb eax,eax; inc`** — the extra
`dec`/`inc` bracket the `!!` idiom. If you wrote `!= 0` and see `dec…inc`,
the source compared against `1`, not `0`.

**Bool argument built with a branch (`push $1` / `jmp` / `push $0`)** → the value
came from an `if/else` (or a `? :` the compiler didn't flatten), reusing flags
already set. A single-expression bool (`x != 0`) instead produces the branchless
`sete`/`sbb` form. Match branchy vs branchless to branchy vs single-expression
source.

---

## Arithmetic

**`sar $1` (no `cltd`/round fixup)** → source wrote `>> 1` on a signed value.
**`sar` preceded by the sign-rounding dance (`cltd; sub; sar`)** → `/ 2` on a
signed value (C rounds toward zero, so the compiler corrects negatives).
**`shr $1`** → `/ 2` or `>> 1` on an *unsigned* value (identical either way).
So `nWidth / 2` and `nWidth >> 1` are different bytes on `int` but the same on
`unsigned` — pick the one that matches.

**`imul` by a constant vs `lea`/shift chains** — VC6 strength-reduces small
constant multiplies. Write the multiply; don't pre-optimize it in source.

---

## Members, locals, and the stack

**Stores through a pointer register in member-offset order** → an inlined
member function that materializes `this` in a register (e.g. `LTRect::Init`,
a CString method). **Direct `[esi+off]` stores** with `esi = this` → plain
`m_field = ...` assignments. The tell for `Init(a,b,c,d)`-style helpers is the
right-to-left argument evaluation: `Init(0, i*h, w, (i+1)*h)` computes the
*last* argument first, so `(i+1)*h` is emitted before `i*h`.

**A local reloaded from its stack slot right after a store through an unrelated
pointer** → the local is *address-taken* somewhere, so the compiler must assume
aliasing and can't keep it in a register. If the shipped code instead keeps the
value in a register across such stores, your source copied it into a plain
(non-address-taken) local first. Classic: after
`GetStringDimensions(&nSizeX, &nSizeY)`, a `int nWidth = nSizeX;` copy lets the
width stay in a register.

**Stack-slot assignment is driven by variable *scope*, not declaration order**
within a scope (proven by repeated probes). If two locals occupy swapped slots
vs shipped, moving one into an inner `{ }` block (or out to function scope)
changes its slot; reordering declarations usually does not.

**Zero-initialization stores** *do* follow declaration order and reuse a single
"zero register" (`xor eax,eax` then several `mov [slot],eax`). The order you
declare `int a=0, b=0, c=0;` is the store order.

**Frame size (`sub $0xNN,%esp`)** is the sum of locals + spills + alignment. If
your frame is larger/smaller, you have an extra/missing local or a buffer of the
wrong size. A shared scratch buffer reused across calls is one local, not one
per call site.

---

## Calls, names, and intrinsics

**`rep movs` / `rep stos` inline** → `memcpy`/`memset`/`strcpy` of a
compile-time-known or small size, or a struct copy/`= {0}`. A `memset(this, 0,
sizeof(*this))` constructor becomes `rep stos` over the object.

**`new T[n]` for a POD with a memset constructor** inlines to a count-guarded
block clear (`lea eax,[n-1]; test; js skip; … rep stos`) and emits an
unreferenced `??_H` vector-constructor-iterator COMDAT. There is **no** null
check in the source — VC6 adds the guard itself.

**Library symbol variants matter:** `strupr` (OLDNAMES) and `_strupr` link to
different symbols (`__strupr` vs `_strupr`). Match the exact spelling the shipped
import uses, or the reloc points at the wrong thunk (and only a link catches it).

**COMDAT section order = source definition order.** The order functions appear
in your `.cpp` is the order they land in the `.obj`. If a lib's function order
differs from shipped, reorder your definitions.

---

## `/O1` (minimize size) idioms

`/O1` trades speed for bytes. If you see these, you're looking at `/O1` code and
must compile with `/O1` to match:

| `/O1` | `/O2` equivalent | meaning |
|---|---|---|
| `cmpl $2,[mem]` | `mov eax,[mem]` + `cmp $2,%eax` | compare straight against memory |
| `pop %ecx` | `add $0x4,%esp` | 1-byte cleanup of one pushed arg |
| `push $0x3c; pop %eax` | `mov $0x3c,%eax` | 3 bytes instead of 5 for a small constant |
| `and dword ptr [x],0` | `mov dword ptr [x],0` | store zero in fewer bytes |
| `push %reg` (value unused) | `sub $0x4,%esp` | **stack reservation**, not an argument |

That last one bites: in a float forward, `push %ecx` followed by `fstps (%esp)`
is the compiler grabbing 4 bytes for a float argument — don't model the pushed
register as a parameter.

## Calls through embedded sub-objects

```asm
mov  0x4(%ecx),%eax     ; vptr read from this+4
add  $0x4,%ecx          ; this = this+4
call *0x28(%eax)        ; virtual slot 10 on the sub-object
```

This is a **thiscall on an object embedded at offset +4** — the engine's
interface implementations are composed this way. Distinguish it from:

- a *pointer* member (`mov eax,[ecx+4]` then `mov edx,[eax]` — two loads, since
  the pointer must be dereferenced before its vptr), and
- a plain member function call (no vtable indirection at all).

Reproduce it with the outer class's own vptr at +0, a **concrete** implementation
object at +4, and dispatch through a pointer to its **abstract** base — VC6
devirtualizes (and stops matching) if the static type is the concrete class.
NOLF1's server math interface was the live example (nolfsrc's guide 06):

```cpp
class CLTServerMath
{
public:
    virtual void _ownvirtual();   // puts this class's vptr at +0
    ILTMath m_common;             // lands at +4
    ...
};

void CLTServerMath::EulerRotateX(LTRotation* pRotation, float amount)
{
    if (!pRotation)
        RETURN_ERROR_VOID("ILTCSBase::EulerRotateX");

    ILTMath* pC = &m_common;      // through a pointer: a real virtual call
    pC->EulerRotateX(*pRotation, amount);
}
```

Calling `m_common.EulerRotateX(...)` on the member directly lets VC6 call the
known implementation, and the bytes would not match.

## Where the local lives (and why the frame changed)

VC6 reuses an incoming argument's stack slot for a local once the argument is
dead. That is why some tiny functions carry an `ebp` frame: they take the address
of a local that happens to live in the argument slot.

The effect is order-sensitive:

```cpp
void* val;                       // declared, uninitialised
if (!p) RETURN_ERROR_VALUE(...); // guard
val = NULL;                      // ← init here: slot reuse survives
```

Initialising at the declaration (`void* val = NULL;`) hoists the store above the
guard and forces VC6 to allocate a **separate** slot, changing the frame size and
breaking the match.

## Trust the bytes over the headers

`src/Engine/sdk/inc/` came with the source release, and the Jupiter tree's
headers (`../fear/Dev/Source/runtime`) are four years later than the engine;
neither always describes the shipped engine exactly. (In NOLF1 the SDK headers
were a later era than the binaries; NOLF2's SDK is the right era, which helps,
but has not been proven slot for slot.) Types and signatures are mostly
stable, but:

- **vtable order is not** — verify each slot's argument count from its `ret N`
  before believing the header's declaration order;
- **arguments may be reordered** when a wrapper forwards inward (a real case:
  `GetRotationVectors(rot, up, right, fwd)` forwards as `(rot, right, up, fwd)`) —
  only the push order tells you;
- **not every pointer parameter is validated** — guard sets are data to read off
  the disassembly, not a style to apply uniformly.

## Residual variance — when to accept "near"

All of Monolith's code in NOLF2 is cl 8966 (VC6 SP5), which we hold, and
[`progress/COMPILERS.md`](../progress/COMPILERS.md) records the evidence, so
revision variance -- a large part of NOLF1's residue, which mixed 8168 and
8447 -- is not an explanation here. What remains is either a genuine free
choice the allocator made or a source shape we have not found yet. Mark these
`near`, comment them, move on — and see
[09-codegen-patterns](09-codegen-patterns.md#known-near-classes) for the full
list with worked evidence:

The first two of these were seen between NOLF1's revisions; with one
revision they mean a source shape is still missing (09 has the levers that
moved them):

- **Tail merging** — a duplicated epilogue or a duplicated `call` kept on one
  side and folded on the other. Changes block sizes and the downstream
  register allocation.
- **Deferred-block emission order** — straight-line code and its out-of-line
  blocks (the cold paths) emitted in a different order. Same instructions,
  different layout, different relative jump displacements.
- **Callee-saved register tie-breaks** — a systematic `ebx`↔`ebp` (or
  `esi`↔`edi`) swap when the allocator had a free choice. Everything else
  matches; the registers are just relabeled.

The test: run the normalized diff from [02-the-loop](02-the-loop.md#reading-a-diff).
If nothing but register names and stack slots differ, and the shape is one of the
above, it's a genuine near. If a real instruction, constant, or branch differs,
it is **not** — there's still a source fix to find.

Two more tests before you accept one. First, **check the file's flags**
(`/O1` against `/O2`, `/GX`, `/Ob`): a per-file exception is a finding, and
goes in `progress/COMPILERS.md`. Second, **check every
call the function makes pushes exactly what the shipped call pushes**: a
prototype that is missing an argument produces register pressure that looks
exactly like an allocation lottery (`CNetMgr::CloseConnection` was exactly
that).
