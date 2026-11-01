# 11 · Large functions and the call-graph check

Every other guide here is about reaching **byte identity**: the function you
write compiles to the bytes that shipped, and the oracle proves it. That
standard is what makes this project's claims trustworthy, and nothing in this
guide relaxes it for the work it applies to.

But it has a bias. Byte identity is easiest on small functions: the hit rate
is roughly two in three under 64 bytes and under one in three by 300. Working
only what is most likely to match means working the smallest functions, so the
share of *functions* reproduced runs well ahead of the share of *bytes*, and
the functions left over are several times the size of the finished ones. A
small number of functions over a kilobyte hold a large part of the remaining
code. `tools/progress.py --todo=<target>` lists what is left, largest first;
look at it before deciding what is worth doing.

A 13 KB function is unlikely to come out exact, and the byte oracle credits
nothing until it does. This guide is about that work: how to reconstruct a
large function, and how to prove it is right when the byte oracle scores it at
zero.

**Where this comes from.** This guide was written in nolfsrc on NOLF1's
`d3d.ren`, a renderer built by Intel C/C++ 4.0, and its examples (addresses,
`/Qip`, `/Qrcd`, the dead-`1.0f` rule) are that binary's. Nothing in NOLF2 is
Intel-compiled: `Lithtech.exe` and `server.dll` are VC6 (cl 8966), and the
renderer is linked into the exe as static libraries (`render_a`,
`render_b`). The method -- the acceptance standard, `callseq.py`,
`census.py`, honest holes -- carries over whole; the compiler-specific
details do not. **Read the last section, "Moving this method to an MSVC
target", before applying anything in between**, and treat the icl material
as NOLF1 history. The renderer's largest functions are where NOLF2 will need
this.

---

## What "done" means here

**Structurally correct, not byte-exact.** The same control flow, the same
calls to the same callees in the same order, the same field accesses at the
same offsets, the same constants. Codegen exactness (register allocation,
instruction scheduling, frame layout, block order) is explicitly out of scope.

**Nothing may be guessed.** This is unchanged, and it is the whole reason the
relaxation is safe. Every field offset, constant and branch is still read off
the shipped bytes. A reconstruction that compiles and is wrong is worse than
none, because it looks like progress. Where a region cannot be decoded, it
gets a `// UNDECODED:` banner naming the addresses, and it is listed in the
write-up. **A function 90% decoded with an honest hole is a good result; one
100% written with a guessed hole is not.**

---

## The check

```sh
python3 tools/callseq.py <image> <start> <end> <obj> <symbol-substring>
```

It compares the **ordered sequence of calls** in the shipped function with the
ordered sequence in your object.

* The shipped side is disassembled out of the image between the two addresses.
* Your side comes from the named symbol's `REL32` call relocations, with each
  target resolved to an address where the symbol name carries one
  (`sub_1004b720`) or where another of our objects places it.
* Alignment is by longest common subsequence, so one missing call reports as
  one insertion rather than desynchronising everything after it. That is what
  makes the output a worklist instead of a wall of noise.

Exit status is 0 when every resolvable target agrees and the counts match.

### Why it is evidence

A function with 164 call sites whose reconstruction issues 153 of them to the
same targets in the same order is right about its control flow, its branch
structure and its callee set, whatever the register allocator did. Getting
that by accident is not plausible. The check is cheap enough to run every few
regions while you work, and it tells you exactly which call you have missed or
invented.

### What it cannot see

**Call-free code.** This is the one structural weakness, and it must be stated
whenever the result is quoted. `0x1004b720` carries a 3.0 KB region of
straight-line x87 with zero calls in it; that region could be entirely wrong
and `callseq` would still say 153 of 164. Always report the undecoded and
call-free regions *alongside* the percentage, never instead of it.

**Indirect calls, when block placement moves them.** An indirect call carries
no relocation, so the tool can only compare its POSITION in the sequence. When
the compiler sinks a call-bearing cold block below the epilogue (which icl
does routinely), the shipped sequence puts those calls last and yours puts
them where the source has them. The result is an equal number of shipped-only
and ours-only rows, *all indirect*, with the totals matching exactly.

That pattern is benign and recognisable: `0x10061a30` came back 29 shipped
against 29 ours with 25 agreeing, and all eight odd rows were indirect, at
addresses that could be predicted in advance from the disassembly. Check for
it before treating a mismatch as a decode error: equal counts on both sides,
all indirect, is block placement.

**A call to `f+4` where you call `f`.** Under `/Qip` a function with external
linkage gets two entries, a short stack entry that falls into a register entry
a few bytes on, and a same-file caller reaches the register one. So the
shipped call goes to `0x10032f34` where yours goes to `0x10032f30`: the same
function, not a wrong callee.

**callseq accepts this as agreement** when `f` is a symbol it placed, and
prints a `~~` line naming every call it accepted that way, so the figure is
never silently flattered and you can always see how many of your agreements
rest on it. Building the file `/Qip` does NOT fix it at source: icl emits both
entries but routes the self-call to the stack entry, the reverse of the
shipped build. That has been measured; do not spend a build on it.

Corollary: **the check has more signal on call-dense functions.** Sort
candidates by bytes-per-call before choosing. Under about 100 B/call the test
is strong; over 300 it is weak, and you must say what else pins the decode.

**Count the calls with the tool, not by eye or by grep.**

```sh
python3 tools/callseq.py <image> <start> <end> --count
```

Byte-scanning for `0xe8` is wrong in both directions. It counts `0xe8` bytes
that are displacements, immediates or data (0x10016324 scans at 69 calls and
makes 38), and it misses indirect calls entirely, which are 46 of
0x1004b720's 164. The errors do not cancel:

| function | byte-scan | actual | actual B/call |
|---|---|---|---|
| 0x10016324 | 69 | **38** | 168 |
| 0x1004b720 | 135 | **164** | 68 |
| 0x10048180 | 65 | **50** | 134 |
| 0x10019d64 | 27 | **15** | 459 |
| 0x10061a30 | 34 | **29** | 389 |

By byte-scan, 0x10016324 looks like 93 B/call, the best in its target; it is
really 168, which is the difference between the strong band and the weak one.

**Rank by DISTINCT callees, not by call count.** Bytes-per-call measures how
much of a function the test *witnesses*; it says nothing about how much the
test *discriminates*. 0x10021f90 scores 86 of 86 at 45 B/call, and it is the
console-variable table: eighty-six records handed to **one** registrar. A
perfect sequence over 86 calls to one function is far weaker evidence than 38
of 38 across a dozen callees, and much weaker than 153 of 164 through a real
control-flow graph. A table-driven function maximises witnessing and minimises
discrimination.

So rank candidates on the number of **distinct** direct callees:

```sh
python3 - <<'EOF'
import sys; sys.path.insert(0,'tools')
from callseq import shipped_calls
from exedump import Pe
c = shipped_calls(Pe('out/reference/d3d.ren'), 0xSTART, 0xEND)
d = [t for _o, t in c if t is not None]
print(len(set(d)), 'distinct of', len(d), 'direct')
EOF
```

---

## Reading the result

```
symbol ?sub_1004b720@CShadowRenderer@@QAEXK@Z
  shipped calls  164   ours  154
  in agreement   153   (152 by resolved target, 1 by position only)
  shipped-only    11   ours-only    1
```

* **shipped-only**: a call the shipped code makes and yours does not. Usually
  a missing statement, an inlined helper the shipped build called out of line,
  or a CRT function your compiler turned into an instruction.
* **ours-only**: a call you make and the shipped code does not. Usually a
  helper the shipped build inlined, or a statement that is not in the
  original.
* **by position only**: the callee could not be placed, so the two agree on
  *where* a call happens but not on *what* it reaches. Weaker evidence; count
  it separately, as the tool does.

### The census residual on float-to-byte casts: `/Qrcd`

A clipper interpolates five colour bytes per emitted vertex, so it carries
thirty to sixty float-to-int conversions, and at plain `/O2` each one expands
to a twelve-instruction `shld`/`neg`/`or`/`shr`/`and`/`xor`/`cmp`/`test`/
`jge`/`jle` truncation where the shipped code has a single convert. That one
idiom dominates the census of every function in the family. `/Qrcd` (icl 4.0's
"fast float-to-int conversions", and the option that `/QIfist` is not; icl
parses `/QIfist` as something else and silently ignores it) turns it into one
instruction. Measured with `tools/census.py`:

    big2b1b0  residue 1864 -> 807    2883 -> 1596 instr   (shipped 1575)
    big051a0           848 -> 357    2139 -> 1318          (shipped 1523)
    big5dca0           969 -> 323    2351 -> 1499          (shipped 1658)
    big40e10          1728 -> 461    2875 -> 1598          (shipped 1669)

`build/build.mk` carries a `D3D_RCD` group. If your function's census
shows a family of rows differing by exactly the number of byte lerps, that is
this, and you should say "needs /Qrcd" rather than treating it as unexplained.

What `/Qrcd` does NOT close: the shipped code emits a 32-bit `fistpl` preceded
by a float store and reload, and `/Qrcd` emits a 64-bit `fistpll` with no
round trip. Tried without effect: `(uint8)(int32)f`, a named `int32`
intermediate, `double` rather than `float` colour temporaries, `/Op` and
`/Qprec`. It is an open question.

### The CRT residual is a flag: `/Oi-`

The CRT maths and memory functions (`0x1007fc98` sqrt, `0x1007fc90` fabs,
`0x1007fdf4` tan, `0x1007fe1c` atan, `0x100805d0` memcpy) were long taken for
an unavoidable toolchain gap: icl holds them as intrinsics and emits `fsqrt`
where the shipped build calls them. They accounted for a large share of all
missing calls in the d3d.ren reconstructions.

**That was wrong. `/Oi-` disables intrinsic expansion and the calls come
back.** Measured per file, on call agreement, in files that have since been
merged into others: 46/50 -> 50/50, 29/30 -> 30/30, 30/31 -> 31/31,
153/164 -> 163/164, 31/39 -> 39/39, 32/44 -> 36/44. `build/build.mk` carries
the `/Oi-` flag groups (`D3D_OI`, and every `w<N>_*_..oi..cpp` suffix);
its d3d.ren section says which suffix means what. Add a file to one only after
measuring it: the hand-written `d3d*.cpp` files reproduce bytes at their
current settings.

`#pragma function(sqrt)` really does move nothing, and `/Ge` for `_chkstk`
makes things worse (see below). The lesson: "known toolchain gap" is a claim
with a shelf life, and the cheap test is to look for the flag before writing
the residual down.

---

## Method for a function of several kilobytes

Do not decode linearly from the top.

0. **Check the extent first** (`tools/extentcheck.py`, below). Above about a
   kilobyte, a bad row is likelier than a correct one.
1. **Frame first.** The prologue's `sub $N,%esp` gives the local footprint and
   often the whole shape: a 0x100-byte block that ends exactly where the next
   named local begins is one object, not eight.
2. **Call targets name the subsystems.** `grep -rn 0xTARGET src/Engine/runtime/<dir>/`:
   most will already be named by earlier work, and a handful of known callees
   usually identify what the function *is*.
3. **Strings pin it.** A debug format string reached from the function names
   its phases; `0x100a9f70`'s "Find: %d, BSP: %d, Setup: %d, Draw: %d" named
   the projected-shadow pass outright.
4. **Branch targets give the block graph.** Build it before writing a line.
5. **Then decode region by region, writing each region's banner as you go**,
   not at the end: the evidence is freshest when you have just read it.

Run `callseq` as you go. The call sequence is scaffolding: get it right and
the rest of the function hangs off it.

---

## Two operational notes

**Give each worker its own scratch directory.** Several people or agents
working in parallel write helper files (stub headers, disassembly dumps), and
in a shared scratch directory they collide: files change underneath a worker
mid-run. Give each one a directory of its own, e.g. `scratch/<addr>/`, and
uniquely named output files. If they also need to build, give each its own
worktree (`tools/agentwt.sh`), so their objects cannot collide either.

**Write the output file incrementally.** A long decode that is interrupted
(a killed process, an exhausted budget) loses everything not yet on disk.
Append each region, or each function, as it is finished.

## When the call sequence is nearly blind

Below roughly one call per 300 bytes the sequence stops being evidence and
becomes a sanity check. These have carried functions in that band, and a write-
up that leans on them is worth more than one that quotes a clean figure:

**An instruction census with no residue.** Count the opcodes the claimed
structure predicts and show the totals leave no room for anything else
(`tools/census.py` compares both sides). 0x10070d10 is the model: `fmull`
66 = 6×11, `fildl` 60 = 6×5×2, `fistpl` 30 = 6×5, `fstpl` 12 = 6 divides + 6
sunk arms, `fcomp` 12 = 6 low + 6 high epsilon tests, `fdivp` 6, `idiv` 6 =
the six `/40`, `rep movsl` 7 = 6×0xa plus 1×3. A seventh plane, a missing
plane, a third position LERP or a sixth byte would move at least three of
those rows. That is a much stronger statement than "the calls line up".

**Frame arithmetic that decomposes exactly.** `sub $0x1108,%esp` = 4,360
bytes = 24 align + 236 (thirty 8-byte temps) + 2,560 (64 vertices of 40) +
pointers + 12 + 1,320 (six clip blocks of 0xdc) + scratch + six 8-byte `fT` +
one float. Each of the two array bounds is then read off the frame rather than
assumed, independently of any call.

**Expression-by-expression correspondence with a decoded sibling.** Not "it
looks like the same clipper" but a diff, plane by plane, with the constants
dumped and compared.

**The literal pool as a statement-order witness.** icl emits float literals
into the pool in SOURCE order, including ones it later folded into immediates
and never loads. For 0x1000e0e0, 0x100a45e4..0x100a4634 therefore reads as a
transcript of the function's statements: four `2.0f` fixing the u0/u1/v0/v1
order, each `100000.0f` followed by the `0.0f`/`1.0f` that replaces it, THREE
copies of 1/255 proving three separate assignments rather than one reused
local, TWO `0.0f` proving two separate calls, and the four `-100000.0f` in the
sunk blocks' emission order. Nothing else recovers statement order in
call-free code. Check the pool before concluding an ordering is a coin-flip.
(On MSVC targets the pool runs the other way; see the last section.)

### _chkstk is a benign residual; do not try to close it with /Ge

A function with a large frame opens with `mov $<size>,%eax ; call 0x100805a0`,
the stack probe. Our build does not emit one, so it shows up as a single
shipped-only row at the function's first instruction. Recognise it and move
on.

`/Ge` ("enable stack checks for all functions") DOES close it, and makes the
result worse. Measured on 0x10060010: without it, 29 of 30 with one
shipped-only; with it, all 30 agree but NINETEEN ours-only appear, because
under `/Ge` icl stops inlining functions the shipped build inlined. Trading one
known residual for nineteen unknown ones is not an improvement.

### Two things that cost calls and are cheap to get back

**A tiny accessor spelled as a field read makes no call at all.** 0x1005dca0
was at 1 of 4 because its source read `m_pData` and `m_nCount` where the
shipped code calls `0x1000a670` and `0x1005f780`, two-instruction accessors
the original build did NOT inline. Declare them as member functions, declared
but not defined in the file, and icl has to emit the calls. That alone took it
to 3 of 4. Look for this whenever ours-only is 0 and shipped-only is a run of
small, high-caller-count targets.

**An arm-order coin-flip is not a coin-flip when either arm makes a call.**
The same function's opening `if` looked like two indistinguishable spellings.
It is not: `if (A && B) {cold} else {hot}` emits the cold arm inline, and
`if (!A || !B) {hot} else {cold}` sinks it. The instructions are identical and
only the ORDER differs, which is exactly what this check reads: 3 of 4 with an
equal shipped-only/ours-only pair, against 4 of 4. One build settles it. This
makes a block-placement pair out of DIRECT calls, where the benign pattern
above is indirect: equal counts alone do not make a pair benign, so try the
other spelling before recording it.

### Completely blind: 0 of 0 is not agreement

0x100051a0 is 5,786 bytes containing **not one call**, direct or indirect:
d3d.ren's six-plane clipper standing alone as a function, reached only through
a `0x440(%ebx)` slot. `callseq` prints `NO CALLS IN RANGE -- this check is
VACUOUS here` for such a function. If you see that line, the instruments above
are not supplementary evidence, they are the *only* evidence, and the write-up
has to carry all of them.

That function is also the reason to decompose the census rows you would rather
wave away. `flds` 106 and `lea` 60 look like noise; broken out by operand they
are the load-bearing ones. `lea` 60 = 20 lea-nop pads + 40 real, and the 40
split 12/6/12/**10**, where the 10 rather than 12 says pass 6's `pOut += nIn`
is dead. No call, no constant and no frame slot shows that.

### Run tools/extentcheck.py first

    python3 tools/extentcheck.py out/reference/d3d.ren 0x1005dca0 6368

It runs the extent checks mechanically: `ret` count, `push %ebp` frames and
whether padding precedes them, branch targets leaving the range or landing
mid-instruction, whether the start is a `/Qip` stack or register entry, and
whether the body ends before the row does. It is a report, not a verdict: it
says where to look, and the evidence still has to be read. It was validated
against known rows, defective and correct, and catches the defective ones
without firing on the correct one.

What a sweep of every d3d.ren row of 1,000 bytes or more found, which is worth
knowing before you read your own function's report:

* **Rows addressed at a `/Qip` REGISTER entry** are the commonest defect: the
  real function starts 4 or 8 bytes earlier at its stack entry (8 when it
  takes two register arguments, so let the tool compute it). The test is
  whether the PRECEDING bytes are argument loads; what the row itself opens
  with is irrelevant, since plenty of icl functions keep no frame pointer.
  Several such functions had been decoded at the wrong address without anyone
  noticing, because the stack entry contains no calls and the call check
  passes either way.
* **Stray branch targets or two prologues** are real extent errors; fix them
  before anyone decodes the row.
* **Zero prologues is NOT a defect.** icl emits large functions entirely
  `%esp`-relative: 0x1004b720 (11,204 bytes) and 0x10043e10 (4,452 bytes) are
  frameless and decode correctly from their rows as given.

**A row that spans five functions.** The worst extent defect found so far:
13,647 bytes covering **five** functions. It was caught by counting `ret`s
(five), prologues (five, each behind lea-nop padding), and checking that
`callseq --count` per candidate function summed to exactly the row's own 68.
Do that arithmetic before decoding anything over about 8 KB: a single function
that large is rarer than a bad row. Record corrected extents with the evidence
(`progress/extent-splits.csv` for a start the enumeration missed; see
`progress/README.md`).

## Recording the result

A large reconstruction is a durable artefact even at zero matched bytes, and
it is only durable if the next reader can tell what is proved from what is
assumed. Every one needs, in its comments:

* the `callseq` figure, **with** the undecoded and call-free regions beside it;
* per region, what it does and what pins it;
* every `// UNDECODED:` gap listed explicitly, with addresses;
* every coin-flip stated with **both** exact spellings, so one build settles
  it.

`tools/decoded.py` and `tools/decodedlt.py` count the bytes under structural
reconstruction and how well each is proved, which the byte scoreboard does
not (see `tools/README.md` for their state in this tree).

---

## Why this is worth doing at zero bytes

More than once, a single finding has retired a whole class of "impossible"
functions at a stroke: `/Qip` for the register-passing convention, `/Od /Ob1`
for the local driver, `/Oi-` for the CRT calls. **When one of those lands, a
stockpile of structurally correct reconstructions converts together, and if
the stockpile does not exist, the finding has nothing to act on.**

The decode is the irreplaceable part. Byte-exactness on top is frequently a
source-shape lottery: most of server.dll's size-exact near-misses have been
taken to exhaustion across every compiler revision held. Spending a week
converting one 11 KB near into a match is a far worse trade than spending it
decoding a second 11 KB function.

---

## Moving this method to an MSVC target (Lithtech.exe, server.dll)

Everything above was learned on NOLF1's d3d.ren, which is **Intel C/C++
4.0**. NOLF2's `Lithtech.exe` and `server.dll`, the renderer included, are
**MSVC 6**, and a good deal of the apparatus is compiler-specific. These were
probed in nolfsrc against `cl` 8447 at `/O2` (NOLF2 is 8966), so that icl
lore is not carried over to an MSVC binary by mistake.

**What does not transfer**

* **The dead-`1.0f` rule is icl-only.** MSVC 6 emits ONE `1.0f` for three
  `1.0f/x` divisions; it pools them. So a spare constant is NOT a division
  marker here, and counting dead constants counts nothing.
* **`/Qrcd` has no analogue and is not needed** (see below).
* **The `/Qip` two-entry offset does not exist**, so `extentcheck`'s
  register-entry walk-back and its overlap check (a row ending inside the next
  function's stack entry) never fire. They were the two commonest defects in
  d3d.ren. Their silence on an MSVC target is NOT evidence that an extent is
  right, and the tool says so in its output.

**What transfers, with a twist**

* **The literal pool is still a statement-order witness, but REVERSED.**
  Source order 3.25, 5.75, 7.125 in one function emits as 7.125, 5.75, 3.25.
  Read the pool backwards on MSVC and forwards on icl. (Measured in a single
  COMDAT, so this is emission order and not a link artefact.)

**What is better here**

* **A float-to-int cast is a CALL.** `(unsigned char)x` at `/O2` compiles to
  `call __ftol` with the result in `%al`. On d3d.ren those conversions were
  inline and invisible, thirty to sixty unwitnessed sites per clipper and the
  largest census residue of all. On MSVC every one of them is a row the call
  check SEES, so evidence density is materially better.
  In NOLF2's `Lithtech.exe` the `_ftol`-like helper (retail 0x567936,
  1,516 callers) and `__chkstk` (0x567648) sit in the SecuROM pages, so
  calls to them name an address the enumeration has no row for; read them
  as `_ftol` and `_chkstk` (`docs/engine/anatomy.md`, section 2).
* A multiply by 2.0f becomes `fadd %st,%st(0)` with no literal emitted at all,
  so do not go looking for a pool entry for it.

**What still applies unchanged:** the call-graph acceptance standard;
`callseq` and `census.py`; quoting what fraction of the bytes the check
witnesses; frame arithmetic with the slots dumped; sibling correspondence; the
accessor trap (a tiny accessor spelled as a field read emits no call);
arm-order being decided by call order rather than being a coin-flip; and
writing the output file incrementally.
