# 10 · Upgrading a near to identical

A **near** is a function we have written whose machine code is not the shipped
machine code. It is not a failure: a near means the shape is understood, the
types are right, and the remaining difference is small enough to name. But a
near is also the only kind of reconstruction that has *never been proven*. A
byte-identical function **is** the shipped code; a near is our guess at it,
and it has to be executed (in our linked engine images, by `make test` /
`tools/playtest.sh`) before anyone can believe it.

This guide is about closing nears. It assumes you can already read VC6 codegen
([03](03-reading-disassembly.md)) and know the fingerprint catalogue
([09](09-codegen-patterns.md)); what follows is the method and the order.
It was written in nolfsrc on NOLF1's engine; the examples' names and
addresses are NOLF1's.

---

## Where the worklist comes from

```sh
python3 tools/progress.py --nears[=target]
```

NOLF2's images have no symbols, so `progress.py` pairs each unmatched
function of ours with a shipped *address* -- by bytes, by name
(`sub_<addr>`), by object and by link order (`progress/README.md`) -- and
that pairing is a heuristic you have to verify (see below). (nolfsrc also
had static libraries with symbols, matched by mangled name with
`libfndiff.py`, which cannot be wrong about which function you are looking
at. NOLF2's release ships no prebuilt library, so every near here is a
paired one.)

---

## Triage: work the worklist, closest first

```sh
python3 tools/progress.py --nears=server
```

One line per near, closest first (NOLF1's, for the format):

```
target         shipped        ship   ours  delta  symbol
server.dll     0x1002c8aa     99     99     +0  commonphysics.obj:?Set@GlobalForceControl@@…
server.dll     0x10030cac     19     18     -1  smgr.obj:?si_GetClientRefInfoFlags@@…
…
N near-matches (M already size-exact)
```

Then, for one function:

```sh
# NOLF1's server.dll and object path
python3 tools/fndiff.py 0x1002c8aa src/engine/server/Release/commonphysics.obj \
    '?Set@GlobalForceControl@@QAEXPAV?$_CVector@M@@@Z' --image=out/reference/server.dll
```

Two numbers at the top of the `fndiff` report decide how much attention a near
deserves, and they say more than the byte delta alone:

| signal | what it means | what to do |
|---|---|---|
| same size, same instruction count, **0 mnemonic blocks** | every instruction agrees; only *operand values* differ | one wrong constant, field offset or register; look at the byte list, it is usually a single line |
| same size, same count, 1–3 blocks | one local decision went the other way | the fix catalogue below; expect one or two experiments |
| same size, **different** instruction count | one construct expanded differently | a shape difference: a loop form, a call, an inlined operator |
| sizes differ by 10% or more | a different shape, or not the same function at all | check the pairing first (below) |

**The pairing is a heuristic: verify it before you believe it.** `progress.py`
pairs each unmatched function of ours with the best remaining shipped address
by length and byte agreement. That is good enough to stop a reconstructed
function being counted as `todo`, and not good enough to trust when you are
about to change source. Real mispairings that have turned up:

- `CFixedCollection<CCollElem08>::Reserve` paired to a function whose element
  size is 4, not 8. The tell was `shl $2` in the shipped code where ours has
  `shl $3`.
- `CFixedCollection<CCollElem28>::AllocItems` paired to a 20-byte-element
  allocator (`lea (%esi,%esi,4); shl $2` is ×20; ours is ×40).
- `CServerThread::CServerThread` paired to `LThread::LThread`, which had not
  been written at all.

So **read the shipped disassembly and check it is the function you think it
is** before diagnosing anything. An element size, a structure offset or a
string reference settles it in seconds. Our source usually carries the address
it was reconstructed from in a comment; if that address and the paired address
disagree, the pairing is wrong.

---

## Three outcomes, and telling them apart early

Every near resolves into one of three things, and knowing which one you have
saves more time than anything else in this guide.

**1. A real source fix.** The shipped code does something ours does not, for a
reason expressible in C++. These are the ones worth working. They usually show
as a small block count with a *structural* difference: a different addressing
mode, an extra load, a value kept in a register across a call.

**2. Not a near at all.** The paired shipped function is one we never wrote,
or one we wrote twice. Both have happened:

- `LThread::LThread` (0x1001587d) was missing. The class had no declared
  constructor, so VC6 inlined the compiler-generated one into every derived
  constructor, and `CServerThread::CServerThread` got paired to it. The tell
  was the shipped code zeroing **two** fields where our class had one at that
  offset. Declaring the base constructor out of line fixed both functions at
  once: the derived constructor now *calls* it, as the shipped one does.
- A file of six node-plane tests duplicated what `worldsim.cpp` had since
  reconstructed as the box projections: the same six shipped functions,
  twice, and six nears that were really one duplicate file. Before writing a
  new function, search the tree for the shipped address you are working from
  (`grep -rn 0x<addr> src/`); `tools/dupes.py` finds addresses that more than
  one of our symbols reconstructs.

**3. A documented class.** The difference is a free choice the register
allocator or the scheduler made, and no source shape moves it. These get
written up (see the last section) and left. Do not rediscover them: the
existing write-ups list what was already tried.

---

## Probe the compiler instead of guessing at it

The fastest tool in this guide is a throwaway translation unit. When a near
comes down to "which source form gives *this* instruction", do not iterate on
the real file. Write the candidate forms as separate functions in a scratch
TU, compile it once, and read all the answers at the same time. In
`make shell`:

```sh
mkdir -p out/probe
cat > out/probe/zzprobe.cpp <<'EOF'
typedef unsigned int uint32;
extern void* Alloc(void* p, int a, uint32 n);
struct C { uint32 pad, items, spare, growby; void* f1(uint32, void*); … };

void* C::f1(uint32 n, void* pA) { … growby + n … }      /* the folded add   */
void* C::f2(uint32 n, void* pA) { uint32 g = growby; … } /* the shipped form */
EOF

source build/env.sh
run_cl /nologo /MD /W3 /O1 /D WIN32 /D NDEBUG /D _WINDOWS \
      /c /Foout/probe/ out/probe/zzprobe.cpp

python3 tools/dumpfn.py out/probe/zzprobe.obj '?f1@C@@QAEPAXIPAX@Z'
```

Use the *target's* flags (`/O1` for `server.dll`, `/O2 /GX` for
`Lithtech.exe`; the project file's are what `build/build.mk` uses -- copy
them from the object's `.cmd` file beside it). Keep probes out of `src/`, so
no build picks them up.

Probes settle positive and negative questions alike. Firm negatives found this
way include: no subscript form moves a SIB's base/index roles, and no
permutation of a dot product's three terms reproduces a particular shipped FPU
order. The negatives are worth as much as the positives: they turn "not tried
yet" into "not reachable", which is the difference between a near that keeps
costing time and one that is finished.

A probe also answers questions the real file cannot. Six permutations of one
expression, or four ways of writing one subscript, cost one compile in a probe
and one full rebuild-and-diff each in the tree.

---

## The fix catalogue, in the order it pays

### Count the calls, and count the pushes

Do this first, on the whole worklist at once: for every near, compare the
number of `call`, `push` and `add $N,%esp` instructions on each side of the
`fndiff` mnemonic diff. A disagreement is always a source fact (a missing
statement, a wrong prototype, a free function where the shipped code has a
thiscall), never a scheduling choice, so it is the one class of residual
guaranteed to be fixable. Examples:

- `GetCurAnimLength`, where a stale free-function declaration produced a
  cdecl `push`+`call` in place of a thiscall on the model animation;
- eight collection `Assign`/`AddFrom` instantiations, where the shipped
  `lea` of a scratch buffer plus a bare thiscall was the element type's
  **destructor**, run explicitly on the copy the walk had just made.

Neither was visible from the byte delta: the first was size-exact and the
second eight bytes short of a two-hundred-byte function.

### Read a member into a local before using it in an expression

`mov mem,%eax; add %reg,%eax` where ours has `mov %reg,%eax; add mem,%eax`
means the shipped source named the member first. See
[09](09-codegen-patterns.md) for the exact forms that work, and the one place
the rule does not hold (a pointer base folded into an addressing mode; probe
it before believing it).

### Look for the loop's own arithmetic

`lea -0x1(%eax),%ecx` … `movzwl %cx,%edi; inc %edi` in front of a `dec`/`jne`
loop is a post-decrement, `while (i--)`, not a counting `for`. The two run the
same number of times, so nothing but the codegen says which was written.

### Name a repeated member address in a local

The single most productive fix. Where the shipped code addresses a field
through a pointer register at small displacements (`(%eax)`, `0x4(%eax)`,
`0x8(%eax)`) and ours goes through `this` at the real offsets (`0x20(%ebx)`,
`0x24(%ebx)`, `0x28(%ebx)`), the source wants a pointer:

```c
	LTVector* pDir = &m_Dir;

	*pDir = m_Force;

	pDir->x /= fMag;
	pDir->y /= fMag;
	pDir->z /= fMag;
```

`fndiff` prints a hint for this one: *"ship has a lea ours lacks"*.

### Name a value that has to survive a write through a pointer

The other half of that same function (`GlobalForceControl::Set`), and the more
interesting half. Ours reloaded the magnitude from `m_fMag` before each
divide; the shipped code kept it on the FPU stack across all three. The reason
is aliasing: the vector copy writes *through a pointer*, so the compiler must
assume it might have hit `m_fMag` and reload it. The shipped build did not
reload, so the shipped source was not reading a member; it was reading a
local:

```c
	fMag = m_Force.Mag();

	m_fMag = fMag;                 /* the member, written once */

	if (fMag > 0.001f) { … /= fMag … }   /* the local, read three times */
```

Generalised: **if the shipped code keeps a value in a register or on the FPU
stack across any write it cannot prove is unaliased, the source held that
value in a local.** Conversely, if the shipped code *reloads* where ours does
not, ours has a local the shipped source did not.

### Do not wrap a loop in a guard to hoist its test

Tempting and wrong. `CNetMgr::GetPacket` is one byte from identical: the
shipped back edge jumps *past* the loop-invariant flag test and ours jumps
*to* it. The obvious fix, hoisting the test into an enclosing `if` and making
the body `for (;;)`, came out **ten bytes worse**, and so did the same guard
with a labelled backward `goto`. The guard is exactly what gives VC6 the
preheader it duplicates the loop's argument pushes into. The shipped build
hoisted the invariant out of an *unrotated* loop, which none of the compiler
revisions we hold will do; the plain `while` form stays the closest.

The rule: **when a loop's shape is one instruction off, changing the loop's
source form usually makes it worse.** Try it once, keep the shorter one.

### Move a statement across the declarations

The boundary between declarations-with-initialisers and the first real
statement is a real scheduling barrier. `ws_ProjectBoxCheap` was two bytes
short with

```c
	LTPlane*      pPlane  = pProject->m_pPlane;
	CSphereQuery* pSphere = pProject->m_pSphere;

	g_nPhysMoves++;
```

and exact with the declarations left bare and the increment above the
assignments. Declaration *order* inside one scope changes nothing (proven many
times over); this is not that.

### Use the frame size as a checksum, and as a type oracle

`sub esp,N` is free information. Add up the locals your source declares and
compare. A twelve-byte shortfall is a missing vector temporary, usually an
inlined operator's return value. A **four-byte hole between two vectors** means
one of them is not a vector: `ws_MovePoint` had two `LTVector`s filling 24 of
a 28-byte frame, and the missing dword was the second out-parameter being an
`LTPlane`. Changing the type finished the function.

When the frame size matches exactly, the local model is right and the residual
is somewhere else; that is worth knowing before you start moving declarations
around.

### Check the arm order, and which shared block survives

Covered in [09](09-codegen-patterns.md), but it is the most common cause of a
size-neutral residual, so re-read it when a diff shows one jump condition
inverted. The two rules that do the most work:

- A shared exit block at the **very end** of a function means the early
  failures were `&&`-merged into one positive guard with the failure return as
  the last statement. `ws_GetBoxStatus` went from a seven-block near to exact
  on that alone.
- Of two identical returns, VC6 keeps the **second** inline and jumps the
  first forward into it. Where the shipped build keeps the *first* inline and
  jumps backward (`CFileStream::Read` and `Write` both do), no rearrangement of
  the three exits reproduces it.

---

## Before writing a near up

Run the cheap checks, in this order. Each is one command and rules out a whole
class of cause.

1. **Is it the right function?** Read the shipped disassembly. Element sizes,
   field offsets and string references identify it in seconds.
2. **Is it the optimisation flags?** `/O1` against `/Os` against `/O2`,
   `/GX`, `/Ob`. In NOLF1 both alternatives were dramatically worse on
   `worldsim.cpp` (0 matches at `/O2`), which is itself worth recording: a
   negative result stops the next person repeating it. (NOLF1's other cheap
   check, the compiler revision, does not apply: NOLF2 is all cl 8966.)
3. **Does every call push what the shipped call pushes?** A prototype missing
   an argument produces register pressure that looks exactly like an
   allocation lottery. `CNetMgr::CloseConnection` was written up as a lottery
   for a long time because nobody checked.

---

## Writing it up

A near that stays in the tree carries, in a comment immediately above the
function, four things:

```c
// NEAR (89 of 89 bytes): a three-register transposition, and the one place
// the sibling lookup and this one disagree -- the shipped build advances the
// slot pointer in place there and makes a fresh register here, ours the
// other way round. Same instructions, same length, nine differing bytes, all
// of them register fields.
```

- **the two sizes**, so the next reader knows whether the shape is right;
- **what the residual actually is**, in instructions, not adjectives;
- **what was tried and ruled out**: flags and every source shape,
  named. This is the part that saves the most time, and the part most often
  skipped;
- **which catalogued class it belongs to**, if any, so the count of instances
  stays visible. Four instances of one class is evidence about the compiler;
  four unexplained one-offs is not.

Then update the class's entry in
[09-codegen-patterns](09-codegen-patterns.md) so the instance count stays
current.

## When a whole cluster is one fix

A template's instantiations are one function each in the scoreboard and one
piece of source between them, so a cluster of same-shaped nears is worth
finding before any single near is worth working. Single lines that each
closed several functions at once:

| the line | what it closed |
|---|---|
| `((T*)tmp)->~T();` after the copy-out | eight `Assign`/`AddFrom` |
| `nGrow = m_nGrowBy;` before the alloc | two `CTypedCollection::Reserve` |
| the unsatisfiable `&&` arm restored | three `CFixedCollection::Reserve` |

To spot them: sort the worklist by *symbol*, not by size, and look for a
repeated base name. `?Reserve@?$CTypedCollection@V…` eleven times over is one
function to read and eleven to bank.

The same shape has a trap in it. The linker folds template instantiations
where two element sizes produce identical code, and `progress.py` pairs what
is left by size, so the shipped address it names for one instantiation
routinely belongs to another. Two of the three fixes above were diagnosed on a
*mispaired* function and verified against the right one afterwards, by taking
the element stride out of the shipped disassembly (`shl $5` is 32 bytes,
`add $0x60,%edx` is 96) and re-running `fndiff` against the instantiation that
matches it. Always confirm which instantiation you are looking at before
concluding anything about the source.

## Check the build before the source

Some of the biggest single gains have not been source fixes at all.

**The flags.** NOLF2 has one compiler revision (cl 8966) for all of
Monolith's code, so NOLF1's biggest build-side gain -- rebuilding the shared
translation units at the revision the Rich header named, which matched five
more functions at once -- has no counterpart here. The flags do: the
engine's `/O1` and `/O2` are inferred from function alignment, not proven,
and a file built with its own flags looks like a cluster of nears.

```sh
python3 tools/richhdr.py out/reference/Lithtech.exe   # a PE image's inventory
python3 tools/compid.py  <a .lib or .obj>              # per-object compiler build
```

`progress/COMPILERS.md` records what each binary was built with and the
evidence for it.

**Then sweep it per translation unit.** Rebuild each file with the
alternative flags in turn against an otherwise-unchanged set and watch the
*whole-image* total (`build/engine.sh <target> verify`, or
`tools/progress.py`); per-object counts double-count and will mislead you.
In NOLF1 such sweeps found exactly one exception in `server.dll`
(`localdriver.cpp`, `/Os`) and retired "maybe it is the flags" for hundreds
of nears at once.

## Budget

Roughly one experiment per byte of delta, and stop. A size-exact near with one
residual block deserves two or three attempts; a hundred-byte gap deserves a
fresh look at the shape rather than a fix. The nears are not going anywhere,
and the compiler will not change its mind, but the next person's time is worth
more than the byte: a well-written near costs them nothing, and a badly
written one costs them the whole afternoon again.
