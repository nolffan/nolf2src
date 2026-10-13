# 09 · The codegen pattern catalogue

Everything in this file has been *proven* — each entry was the last blocker on
at least one function that is now byte-identical, or is a measured negative
worth not repeating. It is the lookup table you reach for when a function is
instruction-equivalent but a few bytes off, and the reference you read before
writing a new one so you get the shape right first time.

[03-reading-disassembly](03-reading-disassembly.md) teaches you to read VC6
codegen at all. This file is the accumulated case law: the patterns that are
*not* obvious. The first half is ordered by what you see in the disassembly
(control flow, loops, the frame, arithmetic, floating point, classes, calls);
the second half is a list of individual findings, each with the function it
closed.

**Where it comes from.** Almost all of it was learned on NOLF1's engine and
libraries in nolfsrc, compiled by Microsoft Visual C++ 6.0 `cl` 12.00 build
8447 (SP3) for the engine. Function names, addresses and file names
(`src/engine/server/...`, `0x1003...`) are NOLF1's and do not exist in this
tree; the codegen lessons are VC6's. NOLF2's code is all `cl` build **8966**
(SP5), the same optimiser generation, and several findings below were
measured unchanged across 8168, 8447, 8804, 8966 and 9782. A finding that
names a revision ("only our cl 8447 does it") has not been re-measured under
8966: test it before relying on it, and record the answer here. nolfsrc's
entries on Intel C/C++ 4.0 (NOLF1's `d3d.ren`) are not brought over: no
Monolith code in NOLF2 is Intel-compiled.

Two rules govern how to use it:

- **Relocations are masked.** Our verifier zeroes relocation bytes on both
  sides, so absolute addresses — the linker's layout of file-scope globals,
  which string a `push` points at, which function a `call` reaches — cost you
  nothing. You need the *shape* of the data, never its address. This is what
  makes reconstructing code that touches a dozen anonymous globals tractable:
  declare them in any order, get their sizes and types right.
- **A near is a hypothesis, not a verdict.** Before writing one up as
  irreducible compiler variance, check the [known near classes](#known-near-classes)
  below — and check that every call the function makes pushes exactly
  what the shipped call pushes. A wrong prototype looks exactly like a
  register lottery.

---

## Contents

**By what the disassembly shows**

- [Control flow and block layout](#control-flow-and-block-layout)
- [Loops](#loops)
- [Locals, temporaries and the frame](#locals-temporaries-and-the-frame)
- [Integer arithmetic and comparisons](#integer-arithmetic-and-comparisons)
- [Floating point](#floating-point)
- [Structs, classes and vtables](#structs-classes-and-vtables)
- [Calls and conventions](#calls-and-conventions)
- [What the shipped source simply did not do](#what-the-shipped-source-simply-did-not-do)
- [Known near classes](#known-near-classes)
- [Compiler revisions](#compiler-revisions)

**Branches, loops and block layout (VC6)**

- [A short-circuit in a condition saves registers earlier than one in a return](#a-short-circuit-in-a-condition-saves-registers-earlier-than-one-in-a-return)
- [An if/else that starts with the same store hoists it above the branch](#an-ifelse-that-starts-with-the-same-store-hoists-it-above-the-branch)
- [A run of guarded returns hosts its shared exit first; one `||` hosts it last](#a-run-of-guarded-returns-hosts-its-shared-exit-first-one--hosts-it-last)
- [One guard, one shared answer: test for the case that CONTINUES](#one-guard-one-shared-answer-test-for-the-case-that-continues)
- [The shared-exit host: which arm carries the common tail](#the-shared-exit-host-which-arm-carries-the-common-tail)
- [`sub` / `neg` / `sbb` / `and` is a `?:`, not an `if`](#sub--neg--sbb--and-is-a--not-an-if)
- [An empty-bodied `while` gets its first iteration peeled](#an-empty-bodied-while-gets-its-first-iteration-peeled)
- [Loop rotation is decided by the back edge — and by a named exit test](#loop-rotation-is-decided-by-the-back-edge--and-by-a-named-exit-test)
- [`for` rematerialises a loop invariant into both predecessors; `while` keeps one copy](#for-rematerialises-a-loop-invariant-into-both-predecessors-while-keeps-one-copy)
- [`add $-K` on a byte is every spelling; `sub $K` is an if/else](#add--k-on-a-byte-is-every-spelling-sub-k-is-an-ifelse)

**Locals, frame and registers (VC6)**

- [A parameter's stack slot can hold a local whose address is taken](#a-parameters-stack-slot-can-hold-a-local-whose-address-is-taken)
- [A block-scoped `uint32` temp defeats the load-narrowing peephole](#a-block-scoped-uint32-temp-defeats-the-load-narrowing-peephole)
- [Narrowing a parameter in place flips the callee-saved assignment](#narrowing-a-parameter-in-place-flips-the-callee-saved-assignment)
- [A three-way argument choice is three push sites, not one value](#a-three-way-argument-choice-is-three-push-sites-not-one-value)
- [A register rotation is usually a missing named local](#a-register-rotation-is-usually-a-missing-named-local)
- [The frame is the declaration order, and it fixes the rotation](#the-frame-is-the-declaration-order-and-it-fixes-the-rotation)
- [The frame-growth direction is NOT constant, and two of this guide's own examples are on opposite sides](#the-frame-growth-direction-is-not-constant-and-two-of-this-guides-own-examples-are-on-opposite-sides)
- [Two `movzx` passes, and the shipped compiler has only one](#two-movzx-passes-and-the-shipped-compiler-has-only-one)
- [A zero stored to a FRAME slot: `and mem,$0` versus `mov mem,$0`](#a-zero-stored-to-a-frame-slot-and-mem0-versus-mov-mem0)
- [An inlined callee's temporary lives in a dead parameter slot](#an-inlined-callees-temporary-lives-in-a-dead-parameter-slot)
- [The dividing line: ORDERING is source-reachable, ALLOCATION is not](#the-dividing-line-ordering-is-source-reachable-allocation-is-not)
- [`lea X(%esi,%eax,1)` vs `lea X(%eax,%esi,1)`: allocation, not source](#lea-xesieax1-vs-lea-xeaxesi1-allocation-not-source)
- [Dead-parameter-slot homing must be checked against BOTH images](#dead-parameter-slot-homing-must-be-checked-against-both-images)
- [A probe that fails is only evidence when the rest of the function is exact](#a-probe-that-fails-is-only-evidence-when-the-rest-of-the-function-is-exact)

**Floats and vectors (VC6)**

- [A whole-vector copy adjusts the base; a componentwise copy indexes it](#a-whole-vector-copy-adjusts-the-base-a-componentwise-copy-indexes-it)
- [A float clamp: `flds` a constant means one assignment, `movl` means three](#a-float-clamp-flds-a-constant-means-one-assignment-movl-means-three)
- [An FP sum emits its terms backwards; a compound assignment does not](#an-fp-sum-emits-its-terms-backwards-a-compound-assignment-does-not)
- [`_CVector<T>`'s members are not expanded at `/O1`, and that is free work](#_cvectorts-members-are-not-expanded-at-o1-and-that-is-free-work)
- [A three-float store through `fld`/`fstp` is `_CVector<T>::Init`](#a-three-float-store-through-fldfstp-is-_cvectortinit)
- [Operand order on a vector operator is a TWELVE-BYTE FACT, not allocation](#operand-order-on-a-vector-operator-is-a-twelve-byte-fact-not-allocation)
- [Two rules that do NOT hold everywhere -- check before applying](#two-rules-that-do-not-hold-everywhere----check-before-applying)

**Classes, constructors, `new` and `delete` (VC6)**

- [A peeled array constructor says where the array actually starts](#a-peeled-array-constructor-says-where-the-array-actually-starts)
- [A null test right after a call belongs to an inline helper, not the source](#a-null-test-right-after-a-call-belongs-to-an-inline-helper-not-the-source)
- [`delete [] p` on a class with a destructor: the loop runs off the end](#delete--p-on-a-class-with-a-destructor-the-loop-runs-off-the-end)
- [`operator new` / `operator delete` are wrappers, one call deep](#operator-new--operator-delete-are-wrappers-one-call-deep)
- [`new` with a constructor: the failing arm materialises the null and stores through it](#new-with-a-constructor-the-failing-arm-materialises-the-null-and-stores-through-it)
- [A constructor inlines at `vptr + one store + call` and not at two](#a-constructor-inlines-at-vptr--one-store--call-and-not-at-two)
- [`__forceinline` is what expands a global's constructor into its `_$E` initializer](#__forceinline-is-what-expands-a-globals-constructor-into-its-_e-initializer)
- [Two vtables adjacent in `.rdata` count each other's slots](#two-vtables-adjacent-in-rdata-count-each-others-slots)
- [The same function pointer in two slots, stored twice](#the-same-function-pointer-in-two-slots-stored-twice)
- [A virtual called on a global OBJECT devirtualises; the shipped code uses a pointer](#a-virtual-called-on-a-global-object-devirtualises-the-shipped-code-uses-a-pointer)
- [The pad that forgot the vptr](#the-pad-that-forgot-the-vptr)

**Inlining (VC6)**

- [VC6's inlining budget is per function, spent from the end backwards](#vc6s-inlining-budget-is-per-function-spent-from-the-end-backwards)
- [The inliner is forward-only, and `inline` is what admits a big helper](#the-inliner-is-forward-only-and-inline-is-what-admits-a-big-helper)
- [`/Ob1` expands only `inline` and in-class. Position is the SECOND condition.](#ob1-expands-only-inline-and-in-class-position-is-the-second-condition)

**Strings, translation units and the limits of the oracle**

- [A runtime `strlen` proves a variable where a literal would fold](#a-runtime-strlen-proves-a-variable-where-a-literal-would-fold)
- [A scratch translation unit can invent a residual](#a-scratch-translation-unit-can-invent-a-residual)
- [What byte-matching cannot see: constants behind relocations](#what-byte-matching-cannot-see-constants-behind-relocations)
- [Byte-identity is not identity of source, and the count is deliberately shy](#byte-identity-is-not-identity-of-source-and-the-count-is-deliberately-shy)
- [The mixed-compiler theory for the size-exact nears: tested, rejected](#the-mixed-compiler-theory-for-the-size-exact-nears-tested-rejected)
- [What the size-exact nears actually are, and why source work will not move them](#what-the-size-exact-nears-actually-are-and-why-source-work-will-not-move-them)
- [Levers that closed "register allocation" verdicts](#levers-that-closed-register-allocation-verdicts)

---

## Control flow and block layout

**Arm order tells you which branch the source guarded.** This is the single
most frequent blocker, so it comes first. Look at which path falls through:

| shipped layout | source shape |
|---|---|
| success falls through, error is jumped to | `if (ok) { ... } return err;` |
| error falls through, success is jumped over | `if (!ok) { err }` |
| a shared error block *after* the body | one `if (A \|\| B)` — the `\|\|` sinks it |
| a shared error block *between* the checks | two separate identical error sites, tail-merged |
| the error block at the very end | a nested success path |

**Four branches off one `cmp` means a condition VC6 could not satisfy but
would not delete.** `CFixedCollection<T>::Reserve` shipped as the typed
collection's resize with the spare term deleted, which leaves

```c
	if (nItems > m_nItems && m_nItems >= m_nItems + 0)   /* the spare is gone */
```

and this:

```
	cmp %eax,%edi
	jb  arm1        ; <  : the shared store
	jbe eqtest      ; <= : the equality test below
	ja  grow        ; >  : straight past the equality test
	jmp arm1        ; the folded body, cross-jumped onto arm1's copy
```

Two things to read off it. VC6 keeps both branches of an unsatisfiable guard
and folds only the body — so a `jmp` into another arm's tail with no reachable
predecessor is a *deleted* arm, not dead code the source lacked. And it
propagates the range: knowing `nItems > m_nItems`, it proves the following
`nItems == m_nItems` false and jumps the `ja` past it. Worth five to thirteen
bytes in each of eighteen instantiations, and invisible until you count the
branches off a single compare.

**A shared exit block at the very *end* of a function means the failures were
AND-merged.** Where several early tests all jump to one small block sitting
immediately before the epilogue, the source did not write them as separate
`if (...) return X;` statements — it wrapped the success path in one positive
guard and left the failure return as the last statement of the function:

```c
	if (TestA(...) && TestB(...) && TestC(...))
	{
		...
		if (n == 1) return 0;
		if (n) { ...; return Walk(...); }
	}

	return 1;
```

Written as three separate `if (!Test()) return 1;` statements instead, our
build hosts the shared block at the *last* test rather than at the end, and
duplicates it there. `ws_GetBoxStatus` went from a seven-block near to exact
on this alone.

**Which copy of a tail-merged block survives.** Of two identical
`RETURN_ERROR` sites, VC6 keeps the **second** one's block inline and jumps
the first forward into it. Write the first check as a guard
(`if (!ok) RETURN_ERROR;`) and the second inline and you get the shipped
layout; writing the first as a trailing `else` moves the merged block past
everything between them. `GetNodeTransform` and `GetSocketTransform` turned on
exactly this.

**Duplicated epilogues vs one shared epilogue.** Several `return 0` epilogues
mean several separate `if (...) return X;` statements. A single shared
epilogue means the conditions were OR-merged, or the ifs nest around one
return.

**The vanishing null test is an early return.** A `test eax,eax; jne` on an
allocation result that seems to guard nothing is not an empty `if` — it is
`if (!p) return p;` followed by more code. VC6 folds the two identical
returns together *unless something stands between them*; in the collection
allocators that something is the placement-new loop, which is why the test
survives there and disappeared from every empty-body attempt.

**A returning error guarded by `||` gets sunk** past the following code. Small
non-call returns (`xor eax,eax; jmp`) stay inline either way.

**Loop rotation carries the hoist.** VC6 only hoists a loop-invariant into a
register when the loop is *rotated* — the test duplicated so that a preheader
exists to hoist into. Where it keeps one shared test block instead there is no
preheader, and an address constant is re-materialised as `push $imm` at its
single use. A named pointer variable does **not** force the hoist: VC6
constant-folds a pointer-to-global straight back into the immediate.

**`or dword ptr [x], 0FFFFFFFFh` is an assignment**, not a bit-set: it is how
VC6 writes `x = -1` (four bytes against seven for `mov`).

**`push $imm` / `pop reg` is `mov reg, imm`** — three bytes against five. It
appears wherever a small constant is loaded, including as a return value
(`push $2; pop eax`).

**A zero already in a register is reused as a constant.** `xor edi,edi` early
in a function, then `push edi` for a literal `0` argument and `cmp edi,edx`
for a `!= 0` test, is one materialised zero serving a loop counter and every
zero comparison. Don't read the early `xor` as an initialisation the source
asked for at that point.

---

## Loops

**Loops want the array indexed, not walked.** Where the source indexes
`p[i]`, VC6 strength-reduces to a pointer it advances — often keeping *both* a
pointer and a byte offset. Source that walks an explicit pointer instead
usually comes out a byte or two different. Write the indexed form.

Its converse: a pointer walk biased to the middle of the element
(`fadds -0x8(%eax)` … `fadds (%eax)` … `add $0xc,%eax`) is still an indexed
source loop; the bias is the scheduler's, not yours.

**`while (n > 0)` and `while (n)` are different on an unsigned.** The first
gives `jbe`, the second `je`. Not interchangeable.

**`lea -0x1(%eax),%ecx; movzwl %cx,%edi; inc %edi` before a down-counting loop
is `while (i--)` on a sixteen-bit counter**, and nothing else. The two
loop forms

```c
for (i = 0; i < nCount; i++)     /* movzwl nCount, then dec/jne */
i = nCount; while (i--)          /* lea -1; movzwl; inc, then dec/jne */
```

run the same number of times and differ by two instructions. The reason is
that a *post*-decrement has to produce the decremented value, so the `lea` is
the loop's own arithmetic and not a strength reduction VC6 can fold away; the
`for` form lets it collapse the whole trip count to one `movzwl` of the limit.
Read the extra `lea -1` / `inc` pair as a post-decrement in the source.
`LMessageImpl::ReadMessageFL` closed on this.

**The cursor-alias walk** reproduces the shipped circular-list traversals:

```c
pRec = pCur;
pCur = (pCur->m_pNext == pTail) ? NULL : pCur->m_pNext;
```

**Contiguous ascending frame slots are an array.** Twenty-four stores that
walk `-0x88`, `-0x84`, `-0x80`, `-0x7c` … upward in order are
`LTVector v[8]`, and no amount of reordering separate named locals reproduces
it. Conversely, values shuffled between the FPU stack and integer registers
and stored out of order are *common subexpressions* of many separate
assignments — the eight box corners are twenty-four assignments from six
distinct expressions, and VC6 does the CSE.

**A loop counter accessed as `incl [mem]` / `cmpl [mem]`** with a kept dead
store, and a provably-once loop left unfolded, means writes through a
`volatile long*` into a dead parameter slot. Plain locals, address-taken
locals and `long[1]` all fold.

---

## Locals, temporaries and the frame

**Scope, not declaration order, assigns stack slots.** Proven by repeated
probes: moving a declaration within a scope changes nothing; putting it in an
inner block changes everything. Zero-init stores, however, do follow
declaration order (and pick a "zero register").

**Scope splits a temporary's live range into the dead parameter slot.** Where
a temp's address is passed to a call repeatedly — `ReadFloat(&f)` three times,
each followed by a store to `vec.x`/`.y`/`.z` — the shipped code uses a real
local for the *first* call and the now-dead parameter slot for the rest,
because the parameter got cached in a register in between. One function-level
`float f;` never reproduces it. Give each read-and-store pair its own block:

```c
{ float f; pMsg->ReadFloat(&f); vec.x = f; }
{ float f; pMsg->ReadFloat(&f); vec.y = f; }
{ float f; pMsg->ReadFloat(&f); vec.z = f; }
```

`LMessageImpl::ReadVectorFL` and `ReadRotationFL` turned on this alone. Do not
widen a scope over a consuming loop, though — that puts the temp back in a
local of its own.

**A dead parameter slot also hosts ordinary temporaries.** A computed value
stored to `0xc(%ebp)` when the third parameter is never read again is just a
local; don't invent a member for it.

**Name a repeated address in a local.** Writing the same member-address
expression twice — `&pObj->m_StandingLink`, `&pMgr->m_Link8c4` — makes VC6
recompute it with a fresh `lea` each time. A named local pointer gets one
`lea` and the register reused, which is what ships. The converse bites too: a
local for something the shipped code recomputes costs a register and a byte.
When a function is size-exact with one `lea`/`add` disagreement, try this
first.

**Order the loads before the head.** Where the shipped code loads a list's
first link out of a slot and *then* advances the same register onto the head,
source that computes the head first keeps both alive and costs a register:

```c
pCur  = pX->m_Head.m_pNext;   /* first */
pHead = &pX->m_Head;          /* second */
```

**A value reloaded from its slot right after a store through an unrelated
pointer is an address-taken local** — the compiler must assume aliasing. If
the shipped code keeps it in a register across such stores, the source copied
it to a plain local first (`int nWidth = nSizeX;` after
`GetStringDimensions(&nSizeX, ...)`).

**Paired field stores off one load need a block-local temp.**
`ServerMessage* pMsg = ref.m_pMsg;` then two stores; repeated member
expressions reload, because the slot is address-exposed.

**A raw-stack temporary is not a constructed one.** The collection's
`Assign`/`AddFrom` walk elements through a scratch buffer the shipped code
never constructs, even for element types that *have* constructors. `T tmp;`
breaks the moment the type gains one; `uint8 tmp[sizeof(T)]` with a cast is
the shipped behaviour for every one of them.

**When two locals initialise from the same walk node and one must spill, VC6
spills the first-declared.**

**Frame size is a checksum, and it tells you types.** Add up the locals you
think exist and compare with `sub esp,N`. A 0x64 frame that your source fills
to 0x58 means you are missing a twelve-byte temporary — usually an inlined
operator's return value. A *four-byte* hole between two vectors usually means
one of them is not a vector: `ws_MovePoint` had `LTVector vHit; LTVector
vShort;` filling 24 of a 28-byte frame, and the missing dword was the second
out-parameter being an `LTPlane` (16 bytes) rather than an `LTVector`. Changing
the type finished the function.

**A statement written before the initialised declarations stays before them.**
`ws_ProjectBoxCheap` put `g_nPhysMoves++` after two pointer locals and came
out two bytes short; moving the increment above them — declarations bare, the
assignments after — put the `incl` where the shipped code has it and the
function went exact. Declaration *order* inside a scope means nothing, but the
boundary between declarations-with-initialisers and the first statement is
real.

---

## Integer arithmetic and comparisons

**`mov mem,%eax; add %reg,%eax` means the member was read into a local first.**
For `m_nGrowBy + nItems` VC6 commutes the add and folds the load into it —
`mov %esi,%eax; add 0x10(%ebx),%eax`. To get the shipped order, the member has
to be a value in its own right before the expression runs:

```c
	nGrow = m_nGrowBy;

	pNew = AllocItems(pAlloc, 0, nGrow + nItems);
```

A separate statement, a `+=`, or an inline accessor all work; writing the
member inside the expression never does, in either operand order. Ten
`CTypedCollection<T>::Reserve` instantiations turned on it.

The rule has a hard edge: it holds for **scalars in an `add`** and not for a
**pointer base folded into an addressing mode**. `&pSprite->m_pAnims[iAnim]`
comes out as `add 0xc(%edx),%eax` whether the table is named or not — four
source forms probed, all identical — so `SpriteControl::SetCurPos`'s
`mov 0xc(%edx),%edx; lea (%edx,%eax,1),%esi` stays a near.

**`lea 0x1(%eax),%edi` is a new value; `mov %eax,%esi; inc %esi` is an update.**
Same three bytes, and the distinction is where the `+ 1` was written:

```c
	uint32 nLen = strlen(pStr) + 1;         /* mov + inc: the variable *is* n+1 */
	dhash_FindElement(hash, pStr, nLen);

	uint32 nLen = strlen(pStr);             /* lea: a temp beside the length */
	dhash_FindElement(hash, pStr, nLen + 1);
```

In the second form VC6 commons the two `nLen + 1` into one register and the
length itself dies. `con_InternString` and `con_CreateVar` both closed on it,
and the esi/edi transposition they had been written up for went with it — a
register rotation is often a *consequence* of a misplaced temporary, not a
separate lottery.

- **`jl` vs `jb`** distinguishes signed from unsigned. A signed compare where
  the shipped code has unsigned means a spurious `(int)` in our source; mixed
  int/uint compares promote to unsigned, and the C4018 warnings that come with
  that are original.
- **`sar` without the round-to-zero fixup** means the source wrote `>> 1`, not
  `/ 2`, on a signed value. `shr` is an unsigned `/ 2`.
- **`lea (%edx,%edx,4)` then `shl $2`** is `i * 20` — an array of 20-byte
  records. Read the element size out of the address arithmetic before guessing
  the struct.
- **16-bit read-modify-write stays 16-bit** only if the source operates on the
  field (`m_Flags &= ~bit`) rather than through a local.
- **`uint16` parameters load as `mov ax`** (partial register) at the call
  site, where a `uint32` parameter zero-extends.
- **Operand order survives.** `a == b` gives `cmp a,b` and `b == a` gives
  `cmp b,a`. The same holds for the two arguments of a comparison call: the
  four `Model` name lookups disagree with each other about which side the
  caller's name goes on, and each has to be written the way it shipped.

---

## Floating point

VC6 is built **without** `/Op`, so it reassociates freely. Add order in an
FPU sequence is the scheduler's choice, not the source's — `(z + x) + y` and
`(z + y) + x` can both come out of `x + y + z` in the same function. Do not
chase add order; chase the things below, which *are* source-visible.

**`LTVector::Init(x,y,z)` is three `flds` (right to left) then three
`fstps`.** Three separate component assignments interleave load-op-store per
component. This one distinction decides a dozen functions.

**By-value vector parameters produce `movsl` runs.** `Dot(_CVector v)`,
`Cross(const _CVector v)` and `DistTo(LTVector vec)` all take their argument
by value, so every call copies twelve bytes onto the stack or into a local.
That copy is your evidence for *which* operand is the argument and which is
`this` — and therefore for the operand order: `a - b` copies `b`.

**A vector operator costs two copies.** `vTotal = a + b;` inlines to: copy
`b` into the by-value slot, build the result component-wise into a temporary,
then copy the temporary into `vTotal`. Three twelve-byte slots for one
statement. Writing the three component adds by hand instead is 27 bytes
shorter — `ws_HandleImpact` was exactly that far off until the operator went
back in.

**`Mag`, `MagSqr`, `Dist`, `DistSqr`, `Norm`, `Cross` and
`LTMatrix::Identity`/`Inverse`/`Normalize` are calls, not inline code.** The
engine's own copies of `ltvector.h`/`ltmatrix.h` carry only their
declarations. Our SDK copies define them inline and VC6 declines to inline
them anyway, so `(a - b).MagSqr()` comes out right — don't "fix" the header
when a call turns up where you expected arithmetic. A pleasant side effect:
reconstructing a caller often cashes in the helpers themselves as exact
matches for free.

**A value kept in `st` across a whole loop is a register-allocated local**
whose address is never taken. `fMin = 1.0e37f;` before an eight-iteration
minimum search never touches memory. Equally, a vector local whose `.x` and
`.y` spill to the frame while `.z` stays in `st` is still one plain
`LTVector` — the compiler ran out of stack registers, not out of variables.

**`float / (float)int_var` still emits `fidiv`.** Only a float *temporary*
forces `fild` + `fdivrp`.

**`(2.0f - x) * (2.0f - x)` emits `fsub st(1)` + `fstp`;** a squared temporary
gives the `fld`/`fsubp` pair the shipped code often has.

**`fcomps` then `fnstsw`/`sahf` then `jae`** is one float compare. Read the
sense carefully: `jae` after `fcomps mem` is taken when `st0 >= mem`, and the
operand you loaded is `st0`. Getting this backwards inverts a branch and
costs a day.

**Repeated member-function calls are repeated calls.** Three `GetRate()`
calls in the disassembly mean three in the source; the era code used a local
where it wanted one.

**A vector operator leaves a temp plus a whole-vector copy.** A run of
`flds`/`fop`/`fstps` building three components into consecutive slots,
followed immediately by three `movsl` out of those slots, is
`v = <vector expression>;` — the operator built its return value in a temp and
the assignment copied it. `g_BoxSphere.m_vPoint = *pMax - *pMin;` produces the
by-value copy of `*pMin`, the temp, and the copy out, in that order. Writing
the three component subtractions by hand produces neither copy.

**`VEC_MIN` / `VEC_MAX` are the SDK macros** (`ltvector.h`), and their shape is
unmistakable: an `fcoms` against the other vector, then one arm doing `fsts` to
the destination while the other does an *integer* `mov` of the same float —
`LTMIN(a,b)` evaluates `(a)` twice, so one path already has it in `st` and the
other has to fetch it. Three of those in a row is one macro.

**`push ecx; push ecx; fstpl (%esp); call` is a math call taking a double.**
`fabs` and `sqrt` are reached that way, and the `fcompl` against a `.rdata`
double right after is a *float* source constant widened — read the eight bytes
as a double and you get `0.0001`, not the nonsense a float read gives.

---

## Structs, classes and vtables

**Vtable slot order must be the SDK header's declaration order.** This is
invisible until a function reaches a sibling method through `this` — and then
every slot is wrong at once. Derive the layout from the binary (`ret N` arg
counts plus error-tag strings, `tools/vtabmap.py`) and cross-check against the
header; where an SDK header is from a later era than the binary, the binary
wins. See [07-vtables](07-vtables.md).

**Every `ILTMath` / `ILTCommon` / `ILTModel` slot returns `LTRESULT`, not
`void`.** The two bytes of `xor eax,eax` are the tell.

**Struct return pushes a hidden buffer pointer last.** A thiscall member
returning `LTVector` looks like: `sub esp,0xc`, write the by-value argument,
`push &retbuf`, `ecx = this`, `call`. The callee returns the buffer address in
`eax`, which the caller then copies out with a `movsl` run. Four visible
things for one C++ expression.

**`push ecx` immediately before `fstps (%esp)` is `sub esp,4`** — the value in
`ecx` is irrelevant. Don't read it as an argument.

**Four `movsl` is a 16-byte struct assignment** (an `LTPlane`); three is an
`LTVector`. Count them before deciding what a pointer points at.

**A pointer chain in the disassembly is a member function.** `mov (%eax),%ecx;
mov 0x28(%ecx),%ecx; mov 0x34(%ecx),%esi` is `pPoly->GetPlane()` inlined —
model the accessor, don't write the chain out at every use.

**One template, not two functions.** What looks like a raw allocator and a
separate constructing one is a single template whose placement-new loop is
simply absent for element types with no constructor. Twelve allocators in
`server.dll`, nine with the loop and three without, and no element size in
both lists — so *which* allocators carry the loop tells you which element
types have constructors.

**A bare `lea` of a stack local followed by a thiscall, with nothing pushed,
is a destructor.** In the collection walk it sits immediately after the
assignment that copies the element out of the scratch buffer:

```
	call 0x10019588        ; *pDst = *that      (operator=)
	lea  -0x34(%ebp),%ecx
	call 0x10016b86        ; ((T*)tmp)->~T()
```

The scratch is still raw bytes — no constructor runs on it, because the walk
fills it before anything reads it — but whatever the *copy* now owns has to be
released before the next iteration overwrites the buffer, so the source calls
the destructor explicitly:

```c
	uint8 tmp[sizeof(T)];
	...
	*pDst = *pSrc->GetNext((T*)tmp, &it);

	((T*)tmp)->~T();
```

For element types with no declared destructor the line emits nothing, which
is why one line of source serves every instantiation — and which is why the
call is worth chasing rather than dismissing: it closed eight functions at
once. More generally, **`call` counts that disagree between the two sides are
the single most productive thing to scan a near list for**; a missing call is
always a source fact, never a scheduling choice.

**Base-class padding is real.** A base with fields to 0x05 pads to 0x08
before the derived class's members start. `CWorldBspBase` cost an off-by-four
in `Init` until it was padded explicitly.

**Watch the declared size when you unify two classes.** Making
`CUnknownB28Obj` a typedef of `Model` shrank the type, so `new Model` in the
manager's `Init` allocated 0x20c instead of 0x2c4 and `Init` silently stopped
matching. The function *count* held while the byte total dropped, which is
how it was caught — always read both numbers.

---

## Calls and conventions

**Stack cleanup identifies varargs.** After a cdecl call, a `pop ecx` per call
means the callee was declared **varargs** at that site; a single batched
`add esp,N` covering several consecutive calls means **fixed** prototypes —
VC6 `/O1` defers cleanup only for fixed-prototype cdecl. The same address can
be both: `server.dll`'s `0x1000e3f9` pops at its `dsi_ServerError` varargs
sites and batches in `CServerMgr::Update`, which is a second, fixed
`(char*, int)` prototype.

But **check the revision before concluding** (NOLF1): cl 8447 *merges* a
pending fixed-prototype cleanup into a varargs call's `add esp`, and 8804
never does. A shipped merged `add` across a `memcpy` plus a varargs call
meant pre-8804 there, not a fixed prototype. NOLF2 is all 8966 (SP5,
whose `cl.exe` reports 12.00.8804), so the revision cannot differ between
two NOLF2 sites; which way 8966 behaves here has not been measured.

**A nested call as a `strncpy` argument needs a temp** so both cdecl cleanups
batch into one `add esp`.

**`dllimport` is an encoding.** `call [__imp__f@4]` is six bytes; `call f`
through a linker thunk is five. A TU calling winsock must
`#include <winsock2.h>` *before* windows.h — winsock2's `WINSOCK_API_LINKAGE`
is `DECLSPEC_IMPORT` and plain winsock.h's is not. Same for mmsystem.h
(`WINMMAPI`). Import entry points earn no reconstruction credit; they are not
in `.text` at all.

**`strupr` and `_strupr` produce different link symbols** (`_strupr` vs
`__strupr`). Shipped LT2 code uses the OLDNAMES form.

**VC6's `va_end` writes `ap = 0`** — a visible store.

**`new T[n]` for a memset-constructed POD** inlines to a count-guarded block
memset (`lea eax,[count-1]; jl skip; … rep stos`) and emits an unreferenced
`??_H` COMDAT. There is no null check in the source.

**COFF section order of COMDAT functions is source definition order** in the
`.cpp`. Useful for confirming you have grouped functions into the right TU.

---

## What the shipped source simply did not do

Three closures were not codegen questions at all — the
shipped function does *less* than a careful reader would write, and the
reconstruction has to do less too.

- **`CString::Concat` never calls `SetLength`.** It strlens, expands, copies,
  and returns; appending therefore leaves the stored length short. There is no
  store to the string header after the `rep movs` and no reloc for one, and
  `GetLength()` is expanded inline *twice*, which is also what says there was
  no `length` local.
- **`CButeMgr`'s constructor is not `Reset()` plus a few pointers.** It leaves
  four members uninitialised, sets `m_bSuccess` *false* rather than true, and
  clears two strings with `Empty()` — which is `ShrinkBuffer(0)` — rather than
  assigning `""`, which would be `CopyString`.
- **Two `CButeMgr` getters were missing their `m_bSuccess` stores**, visible as
  a `movb $0x1,0xd(%esi)` in the shipped code with nothing opposite.

The lesson is the diff direction: when the shipped function is *shorter* than
ours the temptation is to look for an optimisation we are missing, and when it
is *longer* the temptation is to look for a statement we are missing. Both
directions can be a statement, and a missing store is easier to see than a
missing optimisation — scan the shipped side for member stores ours has no
counterpart for before theorising about the register allocator.

**An exception frame with no local to unwind is a `try`.** `CustomZAlloc` was
half the shipped size and had no `mov %esp,%fs:0` at all. The shipped code
registers a frame and ends with a funclet — `mov $L,%eax; ret` — which is a
`catch(...)` whose body is `return NULL`, reached by the `throw` two
instructions earlier. A zlib callback cannot be unwound through, so the
exception has to stop in the allocator. Read a funclet at the end of a small
function as a catch block, and remember that a class with no destructor gives
you no frame at all no matter how you write the throw.

**A function-local static goes *after* the surrounding stores.** Five ButeMgr
getters open with `static CRect defVal(...)` and `m_bSuccess = true`. Putting
the flag store first lets VC6 reuse the `1` still in `%al` as the once-flag's
test-and-set bit; declaring the static first makes it load the flag before the
store and materialise the bit separately. Five functions turned on that one
line move.

**A named temporary and an unnamed one are different code.**

```c
CSymTabItem temp(IntType, val);  *pItem = temp;   /* re-addresses the local */
*pItem = CSymTabItem(IntType, val);               /* pushes the ctor's return */
```

Which one shipped is not uniform even within one family: eight of ButeMgr's
eleven `Set*` overloads are the unnamed form and three are the named one,
because the constructors are all defined in the class body and these functions
sit right at the size where VC6 stops expanding them.

**The pointer local's *scope* matters as much as its existence.** Naming
`&pState->m_vMomentum` and `&pState->m_vVelocityAdd` closed `ws_HandleImpact`
outright. The same fix on `ws_ObjectsCollided` only worked with the pointer
declared **inside** the `if` that uses it — at function scope it also folded
the dot product at the top of the function, which the shipped code writes
against the member directly.

**Instruction-count parity is a stopping rule.** When `fndiff` reports the
same instruction count and the same size, and the residual is memory-versus-
FPU-stack or a frame displacement, the source shape is right and what is left
belongs to the allocator. `CSimContext::Setup` and `ws_AddClippedContact` both
reached that state; both are written up rather than chased further.

---

## Known near classes

Document these and move on. Each has been chased to exhaustion at least once.

| class | what it looks like | evidence |
|---|---|---|
| **Shared-exit host** (the big one) | a small exit block referenced twice: the shipped build puts it at its **first** reference and jumps *backward* into it from the second, ours puts it at its **last** and jumps forward from the first. Usually size-neutral | fourteen instances and counting — `CFileStream::Read` and `Write`, `MyServerInterface::HostGame`, `ws_ProjectBox`, all six axis-aligned projections, `CSimContext::ClassifyPlane` (exit host now fixed; 2 insns left), `ws_PushBoxOutOfContacts` (closed -- no layout difference was left once the arithmetic matched), `LMessageList::Append`, `con_AddCommand`, `TCPConnTable::Add`. None of the four revisions and neither `/Os` nor `/O2` moves it. **Source CAN move it.** Guarded early returns host the merged exit on the LAST arm; one explicit if/else chain in which EVERY arm, inner tests included, ends in its own return hosts it on the FIRST arm, as shipped usually has it (`GetConsoleVar`, `se_LoadModel`, `sub_1000e05b` closed this way; an explicit `goto` to the first arm does NOT work). Also closed: one result local set on every arm and returned once, refusal as an `else` assignment (`xfer_HandleMessage`, `str_FormatMessage`) |
| **Tail merge** | 2–3 bytes short, instruction sequence otherwise identical; our build folds a tail the two arms share and the shipped build keeps both copies | the same three as above where the residual costs bytes rather than layout |
| **Cross-jump host lottery** | identical instruction multiset, different case hosting the shared call-tail | `CLTServer::EndMessage2`, 302/302 bytes: TOCLIENT in shipped, TOOBJECT in ours. **Closed:** the shared tail goes to whichever case is LAST in source order; writing TOCLIENT after TOOBJECT made it byte-identical, and the code still lays out in shipped address order |
| **Callee-saved rotation** | systematic `ebx`/`esi`/`ecx` swaps, ±1 byte from a shorter encoding | `ws_HandleImpact` (1 byte), `ws_IsBoxOutsidePoly` (2 bytes) |
| **Shrink-wrapping** | `push edi` deferred past the first block | many |
| **FPU stack bookkeeping** | `fsubrs mem` where shipped has `fld mem; fsub st(1); fstp st(1)`, or one extra spill of a term | `ws_AddClippedContact` (5 bytes) |
| **FPU term ordering** | the same products added in a different order | `ws_Bounce` (4 bytes) |
| **Loop-rotation hoist** | an address constant hoisted into a register vs re-materialised as `push $imm` | `StartQuery` — **closed**: two branches that shared one tail via `continue` each got their own copy of the tail; VC6 merges them and rotates the loop as shipped (test duplicated at 0x100364ad, constant in the preheader at 0x10036416) |
| **Float temp placement** | the shipped build parks a live float in a dead *parameter* slot; ours gives it a frame slot, shifting every offset below it | `ws_ObjectsCollided` (562/562, 7 blocks), `ws_SetupSweptBox` (1 byte), `ws_ShiftBox` |
| **An extra invariant hoist** | ours computes a member's address into a callee-saved register once (worth a byte at each of many uses) where the shipped build re-addresses it every time; ours comes out *shorter* | `ws_ShiftBox` (887/907) |
| **Unrotated invariant hoist** | the shipped back edge jumps *past* a loop-invariant test that ours re-executes; wrapping the loop in a guard to hoist it gives VC6 a preheader it duplicates the argument pushes into, ten bytes worse | `CNetMgr::GetPacket` (394/394, one displacement byte) |
| **Immediate width** | `and $0xfffe,%ax` where ours widens to `and $imm32,%eax`; VC6 narrows per operation, so the `or $1,%al` beside it agrees | `si_SetModelPlaying` (81/80) |
| **movzx elision** | the shipped build zero-extends a byte field before shifting it; ours proves the upper bits are masked away anyway and uses a partial register. **Since closed for `si_GetObjectState`** by an if / else-if / else select (see [the last section](#levers-that-closed-register-allocation-verdicts)); the probes below are what did *not* work: fifteen source forms — the field inline, through a `uint32` local, an `int` local, a `uint8` local, a `volatile uint8` field, a `volatile` local, both operand orders of the shift and mask, `/` and `%` instead, and one- and two-bit bitfields — all narrow to `mov mem,%al`. The only way to get the `movzx` is to make the mask redundant (`>> 1 & 0x7f`), which then loses the `and` the shipped code has | `si_GetObjectState`, `si_GetClientRefInfoFlags` |
| **Zero-store grouping** | ours emits all the constant-zero field stores together in declaration order; the shipped build leaves one after the non-zero store beside it. Size-neutral, and unaffected by source order | the eight `CTypedCollection::Init` instantiations (53/53) |
| **SIB base/index roles** | a scale-1 `mov 0x24(%ecx,%eax,1),%eax` where ours picks the operands the other way round, or `mov mem,%reg; lea (%reg,%idx,1)` where ours folds the load into an `add`. One byte, and probe TUs show no subscript form reaches it — but changing *which pointer variable* the uses go through can flip it (see [the last section](#levers-that-closed-register-allocation-verdicts)) | `SpriteControl::GetNumFrames` (90/90), `SetCurPos` (142/143), `CServerMgr::EndWorld` (197/198) |
| **Frame slot rotation** | same size, same instructions, zero mnemonic blocks, and every differing byte a frame displacement — the shipped build kept one more value in a register | `Assign`/`AddFrom` for the 4- and 8-byte collection elements, the two whose indexing folds into an addressing mode |

Three cautions, all learned the hard way:

- **`CNetMgr::CloseConnection` sat here for a long time as a "register
  lottery".** It was not. Our declaration of the notification slot took no
  arguments and the shipped call pushes the connection; the register pressure
  that created was the entire difference.
- **The physics module's nears are *not* a revision issue.** 8168, 8447 and
  8966 all emit what we emit, contradicting `fndiff`'s hint. A hint is a
  hypothesis to test, not a diagnosis.
- **A near may not be a near.** `progress.py`'s pairing is a heuristic, so the
  shipped address it names can belong to a different function — or to one we
  never wrote. Verify the pairing from the shipped disassembly before changing
  any source; see
  [10-upgrading-nears](10-upgrading-nears.md).

---

## Compiler revisions

**NOLF2 has one.** Every Monolith object in NOLF2's binaries is `cl` build
8966 (VC6 SP5, `toolchains/msvc-6.00-8966`), by the Rich headers, and the
game DLLs, launcher, dedicated server, `ServerDir.dll` and `snddrv.dll`
built with it reproduce their retail Rich headers triple for triple
([`progress/COMPILERS.md`](../progress/COMPILERS.md)). So a near in NOLF2 is
a source shape or a flag, never the revision. The only other compilers in
the images are the DirectX 8.1 SDK's (cl 13.00.9178 and Intel C/C++, inside
`d3dx8.lib`: `middleware`, not ours) and Creative's `eaxguid.lib` (8168,
data only).

**`@comp.id` is exact where the Rich header is only inventory.** Every object
MSVC emits carries an absolute symbol whose low sixteen bits are the
compiler's build number; a `.lib` keeps its objects' symbol tables, so for a
library the attribution is per object. `tools/compid.py` reads it out of a
`.lib` or an `.obj`.

The flags, as known so far (the engine's are testimony until proven per
file; record exceptions in `progress/COMPILERS.md`):

| artifact | compiler | flags | where it is set |
|---|---|---|---|
| game DLLs, `NOLF2.exe`, `NOLF2Srv.exe`, `ServerDir.dll` | cl **8966** | `/O2 /GX`, `/GR` where the `.dsp` says | the `.dsp` files, through `build/build.mk` |
| `snddrv.dll` | cl **8966** | `/O2 /Ob2 /GX` with `/YX` | `src/Engine/snddrv/snddrv.dsp` |
| `server.dll` | cl **8966** | `/O1` (or `/Os`), some `/GX`, no `/GR` | the engine's `.dsp` |
| `Lithtech.exe` | cl **8966** | `/O2 /GX`, no `/GR` | the engine's `.dsp` |

**From NOLF1, for history.** NOLF1 mixed revisions: its `server.dll` was 95
C++ objects of 8447 and 8 of 8168, its renderer Intel C/C++ 4.0, its game
DLLs SP6. nolfsrc's `build/env.sh` carried a `CL_REV=` override to test
revision questions rather than presume them, and the negative result is
worth keeping: the theory that "8168 preserves loop shape and keeps cold
blocks at their lexical position" was **falsified** once the real compilers
were in hand. Shapes that reproduced under no revision were open
source-shape questions, not revision variance -- which is the only kind of
question NOLF2 has.

---

The rest of this file is individual findings, each with the function it
closed (or the measurement that ruled it out).

## A short-circuit in a condition saves registers earlier than one in a return

`return A(p) || B(p);` and `if (A(p) || B(p)) return LTTRUE; return LTFALSE;`
lower to the same twenty-five instructions, and both jump forward to one
shared `mov $1,%eax`. They differ in one byte's placement: the second puts
`push %esi` in the prologue, ahead of the guard that returns before `p` is
ever read, while the first defers the save to the block that needs it.

    ship            ours (return A || B)
    push %esi       call  GetMgr
    call  GetMgr    test  %ecx,%ecx
    test  %ecx,%ecx jne   work
    jne   work      xor   %eax,%eax
    xor   %eax,%eax ret
    pop   %esi      push  %esi        <- the whole difference
    ret             ...

So a shipped function whose prologue saves a register the early-exit path
never uses was written with the short-circuit in an `if`, not in the
`return`. `ci_LoadSong` (0x004095e0) is the worked example.

## An if/else that starts with the same store hoists it above the branch

`ci_SetLightRadius` (0x0040bf30) compares against memory and then stores over
the value it just compared:

    flds  0x8(%esp)          ; the new radius
    fcoms 0x1a8(%ecx)        ; compare against the old, no pop
    fstps 0x1a8(%ecx)        ; store the new one, pop
    fnstsw %ax
    test  $0x41,%ah
    jne   done               ; not greater - nothing else to do

The branch reads the status word directly, so the comparison feeds a branch
and nothing else: there is no `LTBOOL bGrew` local (that spends a `setne` and
a second test, and loads the old value into `%st(1)` instead of comparing
against memory). The store sits between the compare and the branch because
VC6 hoisted it out of an if/else whose arms both begin with it:

    if (radius > p->m_fLightRadius) { p->m_fLightRadius = radius; notify(); }
    else                            { p->m_fLightRadius = radius; }

So a store that appears before the branch that guards its own call site is
not evidence of a local holding the old value - look for the duplicated
statement first.

## A whole-vector copy adjusts the base; a componentwise copy indexes it

Both of these copy three floats, and the shipped form says which was written:

    *pAdd = pCam->m_LightAdd;          add   $0x1c4,%eax
                                       mov   (%eax),%edx        ...

    pScale->x = pObj->m_Scale.x;       mov   0xac(%eax),%edx
    pScale->y = pObj->m_Scale.y;       mov   0xb0(%eax),%edx
    pScale->z = pObj->m_Scale.z;       mov   0xb4(%eax),%eax

`LTVector` is `_CVector<float>`, so the first goes through a generated
assignment that takes the address of the member and works from there; the
second keeps the object in the base register, which is what lets VC6 spend
the base register itself on the last load. `ci_GetCameraLightAdd`
(0x0040b470) is the first, `ci_GetObjectScale` (0x0040ac80) the second.
`LTRotation` is a plain struct and always indexes, so this only separates the
two forms for vectors.

## A parameter's stack slot can hold a local whose address is taken

`ci_GetTcpIpAddress` (0x00408360) has no prologue at all and still passes a
pointer into its own frame:

    mov  0x8(%esp),%edx      ; dwBufferSize
    lea  0x4(%esp),%ecx      ; and this is &sAddress
    push %ecx

The net manager's third parameter is a `unsigned short&` the interface has
nothing to do with, so the source declares a local for it - and VC6 puts that
local in the slot the dead `sAddress` parameter occupies rather than reserving
a new word. So `lea` of a positive offset with no `sub %esp` is still a
local's address, not an argument's.

## A float clamp: `flds` a constant means one assignment, `movl` means three

The same three-way clamp, written two ways:

    m_fAlpha = a < 0 ? 0 : (a > 1 ? 1 : a);     flds  0x4a14d8      ; 0.0f
                                                fstps 0x28(%ecx)

    if (a < 0) m_fAlpha = 0;                    movl  $0x0,0x28(%ecx)
    else if (a > 1) m_fAlpha = 1;
    else m_fAlpha = a;

One assignment whose value is a conditional expression puts every arm's value
through `%st(0)`, so each arm loads its constant out of .rdata and the store
is an `fstps` that VC6 then duplicates into each arm. Three separate
assignments store the constants as immediates and never touch the FPU.
`ci_SetSurfaceAlpha` (0x0040ecc0) is the first form; `ci_SetCameraFOV`
(0x0040b310), which clamps its two arguments in place with if/else and stores
them afterwards, is the second - and shows the same function can hold both.

## A peeled array constructor says where the array actually starts

`ci_CreateObject` (0x0040abc0) builds three twelve-byte file references and
constructs them like this:

    mov  %dx,0xc(%esp)       ; one store, for the first record
    mov  $0x2,%ecx           ; then a loop of two
    ...

`CClientFileRef m_Refs[3]` gives a loop of three. What gives a peeled store
plus a loop of two is a *separate member* followed by an array of two:

    CClientFileRef m_ObjectFile;
    CClientFileRef m_SkinFiles[MAX_MODEL_TEXTURES];   // MAX_MODEL_TEXTURES is 2

The peeled member's constructor writes all three of its fields, two of which
the code immediately overwrites, so only the field nothing assigns - the
local ID - survives dead-store elimination. So the surviving store is at the
offset of whichever field the following code leaves alone, and the loop count
is the size of the real array.

## A null test right after a call belongs to an inline helper, not the source

`CLTDirectMusicMgr::Stop` (0x00440480) empties the pending queue like this:

    loop: mov  (%edi),%esi        ; the list head
          test %esi,%esi
          je   done
          push %esi
          mov  %ebx,%ecx
          call Remove
          test %esi,%esi          ; again, on a register nothing has touched
          je   loop
          ...push it on the free list...

The second test looks redundant — the loop condition proved `%esi` non-null
four instructions earlier and `Remove` cannot have changed a callee-saved
register. It is the bank's own inline free:

    void Free(void* pRecord)
    {
        if (pRecord) { *(void**)pRecord = m_pFree; m_pFree = pRecord; }
    }

VC6 inlines the body but does not carry the caller's knowledge across the
intervening call, so the guard survives. Write the push without it and the
function comes out four bytes short. So a test that looks tautological
immediately after a call is evidence of a guarded inline in the source, not
of a second check the programmer wrote.

## `delete [] p` on a class with a destructor: the loop runs off the end

`CLTDirectMusicMgr::TermLevel` (0x00440230) takes down an array of
sixteen-byte objects, and no hand-written loop reproduces what it emits:

    mov  -0x4(%eax),%ecx      ; the array cookie: the element count
    lea  -0x4(%eax),%ebp      ; the block the allocator actually gave us
    mov  %ecx,%edi
    shl  $0x4,%edi
    add  %eax,%edi            ; edi = one past the last element
    dec  %ecx
    js   done
    lea  0x1(%ecx),%ebx       ; trip count
    loop:
    sub  $0x10,%edi           ; step back FIRST
    mov  %edi,%ecx
    call ~T
    dec  %ebx
    jne  loop
    done:
    push %ebp
    call operator delete

Both `for (i = n - 1; i >= 0; i--) p[i].~T();` and
`while (--i >= 0) p[i].~T();` canonicalise to a pointer that starts *at* the
last element and decrements *after* the call. The shipped form starts past the
end and decrements *before* it, which is the CRT's own `__ehvec_dtor`
algorithm — and with exceptions off VC6 expands that inline for `delete [] p`.
Writing `delete []` is the only thing that reproduces it, and it also gets the
`xor %reg,%reg; mov %reg,<member>` ordering of the pointer's clearing right.
It leaves an unreferenced `??_I` COMDAT behind, exactly as `new T[n]` leaves
a `??_H`.

## `operator new` / `operator delete` are wrappers, one call deep

Four addresses that are easy to conflate, and relocation masking hides the
mistake until the eventual link:

| address | what it is |
|---|---|
| 0x00428fd0 | `dalloc` — the engine's allocator |
| 0x00429080 | `dfree` — decrements the live count, bumps the total, calls the CRT free |
| 0x004290b0 | `operator new` — one argument, calls `dalloc` |
| 0x004290c0 | `operator delete` — one argument, calls `dfree` |

Source that says `dfree(p)` compiles to a call to 0x00429080;
source that says `delete p` compiles to a call to 0x004290c0. Both match
byte-for-byte against either address because the operand is a masked
relocation, so the disassembly is the only thing that tells them apart —
`ci_RelinquishRenderModes` (0x0042df20) really does call `dfree` directly,
and every free in `TermLevel` really is a `delete`.

## A runtime `strlen` proves a variable where a literal would fold

`InitLevel` (0x0043fcd0) builds a path and appends a separator, and the
shipped code measures that separator at run time:

    repnz scas %es:(%edi),%al     ; strlen(sSeparator)
    ...
    rep movsb

Write `strcat(sFullName, "\\")` and VC6 folds the length to 1 and the call to
a two-byte store — sixteen bytes shorter, and wrong. So does
`char* sSeparator = "\\";`, which gets constant-propagated the same way. Only

    static char sSeparator[] = "\\";

keeps the length opaque enough for the `repnz scas` to survive. A visible
runtime `strlen` of something that looks like a constant is therefore evidence
of a `static char[]` in the source, not of a literal.

## A scratch translation unit can invent a residual

`InitLevel` came out thirty-three bytes short in a file of its own, with the
shipped code reporting a refused control file from two byte-identical blocks
where ours cross-jumped them into one. Moved into `clientmusic.cpp` beside the
other nine functions of its class, with no source change at all, it matched
exactly.

VC6's decision to merge two identical blocks depends on how the string
literals they push are emitted, and that depends on what else in the
translation unit uses them. So an isolated harness TU is fine for exploring a
function but is not evidence about its final bytes: re-verify in the real file
before recording a near, or the residual you write down may be one the harness
created.

## `new` with a constructor: the failing arm materialises the null and stores through it

Every allocation in `ChangeIntensity` (0x00440620) guards exactly one store —
the type word — behind the allocator's null test, and leaves the stores after
it unguarded. The failing arm materialises zero into a register and the code
then stores through that register:

    xor  %eax,%eax
    ...
    mov  %ecx,0xc(%eax)      ; on the null path too

That is what `new` gives a class with a constructor: the constructor runs only
when the allocation succeeded, and the assignments the caller writes after it
run either way. An explicit `p = Alloc(); if (p) p->m_nType = ...;` produces
neither the split nor the store through null. So a null arm that materialises
zero and is then written through is `new`, not a written-out allocate-and-test.

## VC6's inlining budget is per function, spent from the end backwards

The same one-line allocator appears in three shapes across `clientmusic.cpp`:
the free-list pop written out inline; the pop left as a call on both paths;
and the pop written out after the grow as well. It is not three different
helpers. VC6 charges each expansion against a per-function budget measured in
the size of what it has already expanded, and it spends that budget from the
*end* of the function backwards — so within one function the later sites get
the richer expansion and the earlier ones degrade.

Three experiments pin it. Giving a function eleven allocation sites instead of
four reproduces every shape in turn, the earliest degrading first. Padding the
helper's body with dead statements walks each site through the same sequence.
And neither the calling function's own size nor its position in the
translation unit moves it at all. A loop body resists degradation longer than
straight-line code.

The practical warning: when the same helper comes out differently at two sites
in one function, that is evidence about the budget, not evidence of two
helpers in the source — and reconstructing it as two helpers will fit those
two sites while being wrong about the source.

**A counter-measurement on lithtech.exe, not yet reconciled.**
Scratch probes on the /O2 lithtech functions behind 0x43beb0, 0x451720 and
0x458e50 found the opposite on two points: in *straight-line* code the
EARLY call sites were expanded and the late ones became calls; and the
caller's own pre-optimisation size DID move it — roughly three dead
statements in the caller bought one more expansion, and dead code inside an
inline callee spent the caller's allowance, nested inlines included. Both
measurements are real; which order applies may depend on loop vs
straight-line placement or on the helper's size, and it has not been pinned
down. The consequence worth keeping: code the original source had but the
optimiser removed still changed what was inlined, which would explain why
reconstructions written without it consistently expand MORE than the shipped
binary. Padding was used only to measure this — never keep dead code to hit
a budget.

## A constructor inlines at `vptr + one store + call` and not at two

Separate from the budget above, there is a hard gate on expanding a
*constructor* at a call site under `/Ob1`, and it sits between three units and
four. Probes in `commonmodel.cpp` (written, measured and deleted) put these on
the inlined side:

* no vptr, two member stores, one call — inlined
* a vptr, one member store, one call — inlined
* a vptr, no member stores, one call — inlined

and these on the called side:

* a vptr, two member stores, one call — **not** inlined

The gate does not care whether the class is a template, whether it derives
from a pure-virtual base, or whether the two stores are written directly or
reached through an inline `Clear()`. It counts the implicit vptr store as one
of the units, which is why the same body inlines for a non-polymorphic class
and does not for a polymorphic one.

`CMoArray<T, C>`'s constructors are exactly the shape on the wrong side of the
gate: vptr, `m_pArray = 0`, `m_nElements = 0`, then a call to the out-of-line
`Init`. So a stack-allocated collection is a *call* in everything we build.

**And the shipped image has one that is inlined** — `Model::Model`
(0x10016cc5), at the first of its two collection temporaries. Every VC6 revision
tried (8168, 8447, 8804, 8966) refuses it at `/Ob1`; `/Ob2` produces it
byte-for-byte, registers included, but also inlines three out-of-line
functions the shipped build kept, so the file is not `/Ob2`. The conclusion is
that the compiler that built that object had one more unit of this budget than
any of ours, and it is the only difference left in a 560-byte function.

Two corollaries worth keeping:

* Under `/Ob1` VC6 will expand a constructor **one level only** — the shipped
  inline of `CMoArray(uint32)` leaves the nested `Init` as a call, while the
  same constructor's own out-of-line COMDAT has `Init` fully expanded inside
  it. `#pragma inline_depth(1)` does not emulate this; it costs 85 functions
  in the file.
* `__forceinline` does not emulate it either: forcing the constructor also
  drags `Init` in, and the site comes out 18 bytes too long rather than 14
  too short.

## An FP sum emits its terms backwards; a compound assignment does not

`f = a + b + c` written as one expression emits the terms **c, b, a**, and it
does that to whatever order you write, so the term that is first in the source
is always last out. Three of the six emission orders a three-term sum can have
are simply unreachable by permuting the source.

Written as an accumulator instead:

```c
f  = a;
f += b;
f += c;
```

the terms come out **a, b, c**, in source order. The value never leaves the
FPU stack, so the two forms are the same size and the same instruction count —
only the order differs, and no frame slot is spent. Making the right operand
of the top-level `+` itself an add (`c + (a + b)`) reaches a third family.

Both spellings are in the shipped worldsim.cpp three lines apart —
`ws_ProjectBoxCheap` uses the flat sum and `ws_ProjectBox` the accumulator —
so this is readable off the bytes, not a style question. It closed
`ws_Bounce`, `ws_ProjectBox` and `sub_100131c1`. Falsified while
establishing it: all four compiler revisions tried emit the same order from
the same source, and so does
every optimisation and processor flag tried.

## `add $-K` on a byte is every spelling; `sub $K` is an if/else

`if (c >= 'a' && c <= 'z') c -= 0x20;` compiles to `add $0xe0,%reg8` in
**sixteen** spellings — `-=`, `= c - K`, `+= 'A' - 'a'`, a ternary assigned
back, `unsigned char`, `signed char`, pointer and index forms, while/do/for,
an `int` counter — across cl 8168/8447/8804/8966/9782 and from both front
ends. The shipped `sub $0x20,%reg8` comes only from an if/else that writes a
*different* variable:

```c
if (range) cUp = (char)(c - 0x20); else cUp = c;
```

Adopting that also flips the whole function's ecx/edx allocation into the
shipped one. Two hash functions fell to this alone.

## `for` rematerialises a loop invariant into both predecessors; `while` keeps one copy

With all three callee-saved registers spoken for, a loop's head address cannot
live in a register. Written as a `while`, VC6 emits one `lea` in the loop
header and aims the back edge at it. Written as `for (init; cond; incr)` with
the head in a named local, VC6 aims the back edge at the *test* and emits the
`lea` in both the preheader and the latch — six bytes bigger, and what the
shipped code has.

Related, and the opposite direction: **naming a list head in a local changes
the register binding of the whole walk.** `while (p != &obj->m_List.m_Head)`
written inline lets VC6 destroy the base pointer with `add $imm,%reg`;
hoisting it to `LTLink* pHead = &obj->m_List.m_Head;` makes it compute the
address into a fresh register with `lea`, preserving the base and rebinding
every register in the body. Same size. The lever is the loop *condition*, not
the declaration.

## Loop rotation is decided by the back edge — and by a named exit test

cl 8447 reproduces an *unrotated* loop — one test block reached by both the
entry and the back edge — exactly when the back edge is an unconditional
`jmp`, and rotates it (peeling the head test and duplicating it at the bottom)
when the back edge is conditional. Most source shapes do not move it: while
with `continue`, `for(;;)` with the test as a `break`, `for(;;)` with it as an
early `return`, and a literal backward `goto` all give the rotated code, under
every revision tried.

One shape does. `FillAvailableRezList` (`NOLF.exe` 0x004015e0) has a single
test at the top and an unconditional jump back, and only this reproduces it:

```c
while (TRUE)
{
	int nRet = _findnext(hFind, &fileinfo);
	if (nRet != 0)
		break;
	...
}
```

Five forms without the named result — `for(;;)` + `break`, a return in the
loop, a backward `goto`, `do`/`while(TRUE)`, `while(!_findnext(...))` — all
rotated. Naming the call result that feeds the exit test is the lever.

One thing that *does* buy the rotation is widening a compare: spelling a bound
check against a `uint16` member leaves the unrotated form, and spelling it as
the full dword the shipped bytes compare makes VC6 rotate — which then creates
a preheader and hoists two other members into it. The rotation, the hoists and
the rebinding are one decision, not three.

## A block-scoped `uint32` temp defeats the load-narrowing peephole

`x.u16[n] = (uint16)p[2];` compiles to a 16-bit load `mov 0x8(%ecx),%cx`, with
or without the cast, signed or unsigned. Introducing a temp *in an inner
scope* —

```c
{ uint32 nID = p[2]; x.u16[n] = (uint16)nID; }
```

— gives the 32-bit load `mov 0x8(%ecx),%ecx` plus a 16-bit store. A
function-scope temp does not work: it has to stay live across the intervening
call and costs frame.

## Narrowing a parameter in place flips the callee-saved assignment

This is a real source lever for the esi/edi transposition class, not a
lottery. `uint32 nNew = flags & 1;` gives the local a live range starting
where it is defined, which outranks an earlier-defined record pointer and
takes `esi`. `flags &= 1;` starts the value's live range at function entry,
drops it below the record pointer, and produces the shipped esi=record /
edi=flags pairing. The prologue difference that comes with it — which
registers are pushed up front versus shrink-wrapped — is a consequence, not a
second difference to chase.

## A three-way argument choice is three push sites, not one value

`f(a, b, (x && y) ? -1 : v)` materialises one merged value with `or $-1,%eax`
and pushes once. Three separate calls to the same function in nested if/else
give three push sites *and* the EBP frame the shipped code has. That was the
whole of `CMemStream::Read`.

## `__forceinline` is what expands a global's constructor into its `_$E` initializer

VC6 at `/O1` never expands a constructor into the compiler-generated dynamic
initializer — not when the constructor is defined in the class body, not with
plain `inline` out of line, not with the body placed before the object's
definition. `/Ob2` does not do it either: it merges the two initializer thunks
into one 22-byte function, which the shipped build does not have (it keeps the
10-byte `call ctor-body; jmp register` plus a 12-byte `push dtor-thunk; call
atexit`). `__forceinline` on the constructor reproduces the shipped shape
exactly, including the global's address folded into every store and no `this`
register.

## `_CVector<T>`'s members are not expanded at `/O1`, and that is free work

`Mag`, `MagSqr`, `Norm` and `Cross` come out as calls whose COMDATs are
byte-identical to the shipped bodies, while `Dot` and `operator-` do inline.
One call site in `w_PointInPoly` matched four functions. Corollary for reading
disassembly: `movsl` triples interleaved through float work are by-value
`LTVector` parameters, and a member call on the *result* of such an expression
adds one more copy, into an addressable temp used as `this`.

## Two vtables adjacent in `.rdata` count each other's slots

A class's own vtable and its first polymorphic member's vtable land next to
each other, and the gap between them is the first one's slot count.
`0x1004d974` to `0x1004d984` is 0x10, so four slots; `0x1004d9e4` to
`0x1004d9f0` is 0xc, so three. In each case the second vtable is the one the
destructor stores at a member's offset. That fixed the slot counts of two
entirely anonymous classes without a single call site.

Related, for finding work rather than reading it: **sweeping `.rdata` for a
known vtable shape enumerates template instantiations that no reconstructed
code calls.** Scanning for `{deleting dtor, Allocate, Free, Init}` found seven
object banks, and the element size baked into each `Init`'s `sb_Init`
immediate is the only thing separating one instantiation from another under
relocation masking. It also separated a second template — a locking bank whose
`Init` brackets the same two calls with `LCriticalSection::Enter`/`Leave` —
from the first by one pair of extra calls.

## A probe that fails is only evidence when the rest of the function is exact

`se_RegisterModel` was written up as an irreducible ebx/edi rotation, with the
"name the list head in a local" spelling explicitly probed and rejected. It
was rejected only because a *different* fault — a `uint16` field being cleared
with `andw` where the shipped build uses `andb` — changed the register
pressure. Fix that and name the head, and the rotation disappears. So a
register rotation can be two faults at once, and probing one lever at a time
hides the second.

(The narrowing itself is worth recording: VC6-8447 narrows `|= 1` on a
`uint16` field to `orb` but will *not* narrow `&= ~1` to `andb`. Both are
equally safe and the shipped image has both.)

## A run of guarded returns hosts its shared exit first; one `||` hosts it last

Seven bounds tests, each `if (bad) return LTFALSE;`, ending in
`return LTTRUE;`. Written that way the function is size- and
instruction-exact against the shipped code and still wrong: VC6 lays the
shared `return LTFALSE` block out *before* the success return and inverts the
final compare to match. Join the last two tests with `||` — five separate
guards, then one two-term guard — and the shared block moves after the
success return and the final compare keeps its original sense. That was the
whole residual on `AnimTimeRef::IsValid` (0x10016410).

This sharpens the existing shared-exit-host entry rather than contradicting
it. "Hosted at the last of a run of guarded returns" is right about *which*
copy survives; what it did not say is that the *number of statements* in the
run decides where the survivor is placed, so the tell in a diff is a final
compare whose sense is inverted, and the fix is at the join rather than at
the block.

## The same function pointer in two slots, stored twice

A constructor that defaults two callback slots to the same do-nothing body
tells you how many functions the source had. Assign one function to both
slots and VC6 loads its address into a register once and stores from the
register:

    mov  $0x10024cac,%ecx
    mov  %ecx,0x14(%eax)
    ...
    mov  %ecx,0x20(%eax)

The shipped code for CVisQuery::CVisQuery (0x100283c6) instead stores the
immediate twice:

    movl $0x10024cac,0x14(%eax)
    ...
    movl $0x10024cac,0x20(%eax)

Two stores of the same immediate mean two *symbols* at compile time --
two relocations, which the optimiser cannot share -- and therefore two
functions in the source. Only one address survives in the image because
/Gy puts each in its own COMDAT and the linker folds the identical bodies
back together. So an address that appears once can still be two functions,
and the give-away is whether its uses share a register.

The same reasoning runs backwards: if our build shares a register where
the shipped build repeats an immediate, stop looking for a scheduling
lever and add the second definition.

## One guard, one shared answer: test for the case that CONTINUES

The single-guard form of the shared-exit rule below, and the highest-yield
first move there is on a size-exact near. Six functions came down to it, every one of them already byte-count and instruction-count exact
with a single inverted branch as the only difference:

    WriteObjectID (0x1003506e)          CObjModel::FindTracker (0x10025074)
    CObjModel::GetFilename (0x100250b7) CObjWorldModel::IsWorldBusy (0x10024e7f)
    wt_FindNodeForSphere (0x1000d437)   ServerMessage::ReadByteFromEnd (0x1002a1da)

The shape is always the same. A function has one cheap answer that two or more
paths share — `return LTFALSE`, `return 0`, `WriteWord(0xffff)`, `return
pNode` — and a real body. Written with the guard NEGATED,

    if (!pObject)
        return LTFALSE;
    ... body ...

VC6 hosts the shared block at that first mention, ahead of the body, and
inverts the branch. Written with the guard POSITIVE and the shared answer
last,

    if (pObject)
    {
        ... body ...
    }
    return LTFALSE;

it hosts the block after the body and the branch keeps its sense. Same
statements, same instruction count, different bytes.

Three practical notes:

  * In a loop it is `break` rather than a return: `wt_FindNodeForSphere` has
    two "stop here" exits and both have to break, with `return pNode` after
    the loop, so the `mov %ecx,%eax; leave; ret` is hosted once at the end.
  * A two-armed `if`/`else` where BOTH arms end in the shared answer works
    too — `WriteObjectID` has the null test inside both arms of a
    `Verify()==1` test, and VC6 merges the two `0xffff` writes into one block
    at the end, so the source has three call sites and the bytes have two.
  * It is worth trying FIRST, before any register or scheduling theory,
    whenever `fndiff` reports one `[replace]` block whose S line is a
    conditional jump and whose O line is the opposite jump.
  * IT APPLIES TO ERROR MACROS TOO, and that is where it hides. The shared
    answer does not have to be one instruction: `cm_LoadModel2`
    (0x004770e0) ends in a twenty-five instruction `RETURN_ERROR` expansion
    -- push the code, call the setter, read the debug level, maybe print,
    load the code, return -- and the negated form
    `if (!pFileRec) RETURN_ERROR(...)` expands all of it where the statement
    stands. Wrapping the rest in `if (pFileRec) { ... }` and putting the
    macro last moved it from 37 differing instructions to 12; applying the
    same move to the `if (!bMayLoad) return LT_INPROGRESS;` one level down
    closed it completely. So when a size-exact near has a BLOCK rather than
    an instruction in the wrong place, look for the guard that produced it
    and turn it positive -- and then look again inside the body, because
    these nest and each level is a separate rewrite.
  * The tell in the shipped bytes is the TARGET, not the branch: if the
    conditional jump goes FORWARD to a block sitting at the very end of the
    function, past every other return, that block is a trailing statement in
    the source and the guard above it is positive.

## The shared-exit host: which arm carries the common tail

Where several paths end the same way, VC6 emits the tail once and jumps to
it from the others — and *which* path keeps the copy is decided by the
source, not by luck. An explicit `if`/`else` chain hosts the tail at its
FIRST arm; a sequence of guarded `return`/`continue` statements hosts it at
the LAST. Every arm must fall through to the shared tail for the rewrite to
take: keeping the `continue`s and merely adding `else` makes matters worse
(ws_MoveBox went 2038 -> 2023 against a 2134-byte target).

Rewriting guarded returns as an if/else chain closed nine functions in
worldsim.cpp that were previously written off as exhausted: bsp_SphereInside,
bspq_TestSphere, CSimContext::ClassifyAxis and all six
ws_ProjectBox{X,Y,Z}{Pos,Neg}.

Do not confuse it with a *duplicated* epilogue, which looks similar in a
diff and is a different thing. con_AddCommand (0x10005b91) is 61 of 63
because the shipped build restores esi mid-body and gives its early return
a two-byte epilogue of its own, where ours jumps to the single one at the
end. There is no shared tail to re-host: wrapping the body in a positive
`if` to leave one exit still gives 61. Tested and negative — the question
there is whether the epilogue is duplicated at all, and that is not
reachable from the source shape.

## A register rotation is usually a missing named local

When our bytes differ from shipped only in which callee-saved register
holds what — ebx for edi, esi for edi — the reflex is to call it a
lottery and write the function off as a near. Usually it is a symptom.
VC6 assigns registers by how long each value is live, so a value the
shipped source held in a *local* and ours recomputes (or vice versa) gets
a different lifetime and therefore a different register, and the whole
allocation rotates behind it.

Two independent instances:

  wb_MaxDistSqr (0x1000aaee) — 93 of 97 with an ebx/edi swap. Copying the
  incoming parameter to a local, so its argument slot could be reused,
  removed the rotation and closed the function.

  stream_Term (0x10035c49) — 59 of 56 with esi/edi swapped and `push %edi`
  on the wrong side of the loop guard. The list head appeared only inside
  the `while` condition as `&g_StreamList`; giving it a named local
  (`LTLink* pHead = &g_StreamList;`) closed it exactly, shrink-wrapped
  save included.

So before accepting a rotation, ask which value the shipped code keeps
live longer than ours does, and give that value a name. The corollary is
that the rotation and any nearby scheduling difference are usually one
fault, not two — both of stream_Term's disappeared together.

Not every rotation yields: 0x1000c0e7 (CTypedCollection::SetSize) and
se_RegisterModel both survived the same treatment across four revisions.

And before hunting for the missing local, read the frame: the next section
recovers the declaration order off the shipped slots, which moves the whole
allocation at once.

## The frame is the declaration order, and it fixes the rotation

The section above says a register rotation is usually a missing named
local. There is a stronger tool for the same problem, and it reads the
answer off the shipped bytes instead of guessing: **the stack frame tells
you the order the original declared its locals in.**

VC6 6.0 gives every spilled local a slot with a plain bump allocator
starting just under `ebp`, walking down in *declaration order*:

    bump = 0
    for each local that does not get a register, in declaration order:
        bump -= sizeof(local)
        bump &= ~(alignof(local) - 1)

Nothing else moves them -- not first use, not size, not type. So a frame
containing anything narrower than a dword is a fingerprint you can invert.
`Model::LoadChildModels` (0x1001c604) has one `uint16` and one `uint8`
among seventeen slots:

    -0x04 dword   -0x06 WORD   -0x0c dword   -0x10 .. -0x2c dwords
    -0x2d BYTE    -0x34 .. -0x44 dwords

The two-byte hole at -0x08 puts the `uint16` **second**; the three-byte
hole at -0x30 puts the `uint8` **twelfth**. Declaring them anywhere else
shifts every slot below and the whole function stops aligning.

Two riders:

  * Aggregates with constructors are not in that run. They are laid out
    below the scalars, in declaration order among themselves -- in this
    function a 0x20-byte object at -0x64 and a 0x34-byte one at -0x98,
    with the seventeen scalars packed above them.

  * A local that gets a register takes no slot, so slot order is
    declaration order *restricted to the spilled ones*. That sounds
    circular and is not, because the count settles it: get the frame size
    and the slot count right first, and only the order is left to search.

The payoff is that this fixes the rotation as a side effect. Before the
reorder, LoadChildModels held `this` in esi, the stream in edi and its
loop counters in ebx; shipped holds them in ebx, esi and edi. Putting the
declarations in slot order moved all three at once -- `mov %ecx,%ebx`
appeared in the prologue on the first build after, and 34 mnemonic blocks
became 26. Nothing about the register assignment was addressed directly.

Two riders on the rule itself, both found on `w_IsectObjectGeometry`
(0x1000f74e), which came out size-exact at 298 bytes with 108 instructions
and *no mnemonic difference at all* -- ten instructions naming a different
slot was the entire residual:

  * **The run is scalars only.** Locals of four bytes and under are laid out
    first, from -0x4 down, in declaration order; aggregates follow *below*
    them, also in declaration order. LoadChildModels shows the same split
    from the other side -- seventeen scalars, then its 0x20-byte object, then
    its 0x34-byte one.

  * **Within the aggregates, size orders the frame: larger aggregates sit
    lower.** Our cl 8447 sinks a sixteen-byte local below every twelve-byte
    one no matter where it is declared, and the shipped frame had it fifth
    of seven -- which once read as the compiler disagreeing with itself and
    was filed as a cl-8168 candidate. It was not. The source was missing an
    aggregate: the two endpoint vectors were one `LTVector vLocal[2]`
    (`[0]` = from at -0x48, `[1]` = to at -0x3c). A 24-byte array sinks
    under the 16-byte plane, and the frame then comes out exactly as
    shipped; the function is byte-identical. So when one oversized local is
    in the wrong place, look for locals that were really one larger
    aggregate (an array or struct) before blaming the compiler.

One trap worth stating on its own. **Do not reuse one `i` across every
loop.** VC6 6.0 does not split live ranges, so an index used in the first
loop and the last is live across the whole function and claims a
callee-saved register for its entire length -- which is where `this` and
the stream want to live. In this function four early loops each have their
own counter (they stay in registers and take no slot) while a single `i`
covers the last three (it is spilled to -0x4 and incremented in memory).
The shipped code shows you which is which: a counter in memory is one
variable spanning calls, a counter in a register is one that does not.

## Two `movzx` passes, and the shipped compiler has only one

The near table used to carry "movzx elision" as an open probe list. It can be
closed. There are two distinct transformations and they are not the same
question:

  **(A) width-reduction of an already-partial load** -- `mov mem,%ax` becomes
  `mov mem,%al` when only the low byte is used. BOTH compilers do this.
  `si_GetModelPlaying` (0x10031bc8) is byte-identical for us and reads the
  `uint16` at +0x1d8 as `mov 0x1d8(%eax),%al; and $0x1,%eax`; 0x1002e97c is
  the same on `(m_Flags >> 1) & 1`.

  **(B) removal of a zero-extension** -- `movzbl mem,%eax` becoming
  `mov mem,%al`, or `movzbl %al,%eax` disappearing. This leaves the upper
  bits dirty where they were clean. **Only our cl 8447 does it.**

So where a field is genuinely one byte, `movzbl` *is* its canonical load and
there is no wider load for (A) to narrow -- which is why no source shape
reaches these. `si_GetClientRefInfoFlags` (0x10030cac, 19 against 18) and
`si_GetObjectState` (0x10031694, 32 against 29) each need exactly (B) and
nothing else. Declaring the field `uint16` gives our current bytes; `uint32`
loses a byte the other way, and no shift-and-mask spelling reaches (B).

That analysis holds, but calling the two functions irreducible did not:
`si_GetObjectState` later closed by writing the select as an if / else-if /
else chain, which keeps the `movzbl`, plus a header member of the wrong width
(see [the last section](#levers-that-closed-register-allocation-verdicts)).
Try that shape before giving up on a `movzbl`.

## A zero stored to a FRAME slot: `and mem,$0` versus `mov mem,$0`

`w_IsPolyBlocking` (0x10001cad) is size-exact, instruction-exact, and two
bytes out, and the two bytes are one store of zero to a frame slot. The
shipped build reaches it through the `and mem,$0` peephole with the immediate
register-substituted (`and %esi,-0x1c(%ebp)`, where %esi is the
function-long zero); ours emits `mov %esi,-0x1c(%ebp)`.

The counts settle that no source construct distinguishes them:
`and %reg,-disp(%ebp)` occurs ONCE in 112,541 lines of shipped `.text` --
this instruction -- and zero times in 99,402 lines of our objects. The same
idiom on a MEMBER (`and %reg,+disp(%reg)`, where a null test proves the zero)
appears 64 times in ours and matches byte-for-byte. So the pass exists in our
compiler and simply is not reached for a frame slot. It belongs with
*Zero-store grouping* in the near table.

## `sub` / `neg` / `sbb` / `and` is a `?:`, not an `if`

A pointer conditionally nulled shows up two ways, and which one you get is
decided by whether the source wrote a statement or an expression.

    if (p == pHead)          ->   cmp  pHead,%esi
        p = NULL;                 jne  X
                                  xor  %esi,%esi

    p = (p == pHead)         ->   mov  %esi,%eax
          ? NULL : p;             sub  pHead,%eax
                                  neg  %eax
                                  sbb  %eax,%eax
                                  and  %eax,%esi

The second turns "did we arrive back at the head" into a mask over the
pointer with no jump at all: `neg` sets the carry iff the difference was
non-zero, `sbb %eax,%eax` spreads that carry to all 32 bits, and the `and`
either keeps the pointer or clears it. Four instructions and 83 bytes
against three and 79 — the branchless form is *longer*, so this is not a
size choice VC6 made for us; it is the shape of the source.

netbank_Term (0x10025fcd) closed on exactly this, having matched every
other instruction. So whenever a shipped `sbb %reg,%reg` sits next to a
`neg`, stop looking for a flag: the original wrote a conditional
expression where the obvious reconstruction writes a conditional
statement.

## What byte-matching cannot see: constants behind relocations

exematch masks every byte a relocation covers — that is what makes an
unrelocated object comparable to a linked image at all. The cost is that
anything reached *through* a relocation is invisible to the oracle.

A float literal is reached that way. It lives in `.rdata` and is loaded by
address, so `x += 0.001f` and `x += 1.0f` emit identical maskable bytes and
exematch calls both a match. Two real errors sat in this repository behind
that hole:

    CNetMgr::AddRecvBytes      ours 0.001f   shipped 1.0f   (0x1004d20c)
    GlobalForceControl::Set    ours 0.001f   shipped 1e-5f  (0x1004d92c)

The first was found only by accident, when reconstructing the send side made
two `fadds` share one `.rdata` address. The second was found by
`tools/fpconst.py`, written for the purpose: for every function exematch
places uniquely in the image, it walks the object's relocations and, where
one points at a read-only constant of ours, reads the corresponding address
out of the shipped image and compares the constants themselves.

    python3 tools/fpconst.py out/reference/server.dll src/engine/server/Release

Run it after any batch of changes; a clean sweep reports every operand
agreeing.

The general lesson is worth more than the tool. "Byte-identical" is a claim
about the bytes the oracle can compare, and it is silent about every operand
a relocation stands in for — string contents as well as numeric constants.
Where the value matters to behaviour rather than to codegen, it has to be
checked some other way, and a comment recording the shipped constant's
address is the cheapest form of that.

## Byte-identity is not identity of source, and the count is deliberately shy

`exematch` and `progress.py` credit ONE shipped address per matched symbol
(`matched[(fresh or hits)[0]]`). That looks like an undercount, and it is
sometimes — a template body with no element size baked in genuinely serves
several shipped functions, and the extra copies go uncredited.

It is still the right rule, and the reason is worth internalising. Across
server.dll, 309 of our symbols match more than one address, and taking every
hit would add 44; restricting to hits that are *enumerated function starts of
exactly our size* would add 226. Both numbers are traps. Our one
reconstructed `??_GCFileBank` — a 28-byte deleting destructor, mostly
relocation — is byte-identical to twenty-one other classes' destructors that
we have never written. The linker did not fold them (this build's ICF leaves
byte-identical bodies at distinct addresses, proven at 0x10024009 versus
0x1000b207), so they are genuinely twenty-two distinct shipped functions —
and we have reconstructed exactly one of them. The oracle cannot tell which.

So: multiple hits mean the bytes cannot distinguish N functions, not that we
have supplied N. Crediting them would be fabrication. The number this project
reports is shy by design, and the correct response to "my function is
missing from the count" is to check the specific address with `fndiff`, not
to loosen the rule.

Corollary for worklists: a candidate can already be byte-identical before you
write anything, for exactly this reason. Nine of thirty entries in one
collection batch were. Check before reconstructing.

### ...and the two binaries disagree about folding

That proof (0x10024009 versus 0x1000b207) is a proof about **server.dll**.
`lithtech.exe` is a different link and it folds: 0x0042d190 is the surviving
body for EIGHT distinct `CBaseDriver` slots, and 0x0042d180, 0x0042d1b0,
0x00432030 and 0x00432040 each serve two. So in the client an address does
NOT identify which translation unit the surviving COMDAT came from, and a
body reachable from several vtable slots is evidence of folding rather than
of a shared base class. Read `dupes.py` and `vtabmap.py` output against the
right binary's rule; the inference that a repeated address means a common
base is sound for server.dll and unsound for lithtech.exe.

**But the converse does NOT hold, and it caught this project out.**
0x0041e930 and 0x004622b0 in lithtech.exe are the same four instructions
calling the same target (0x0041abe0) — they differ only in the `call`
displacement, which is what ICF exists to collapse — and they were NOT
folded. That does not disprove folding: **`/OPT:ICF` folds COMDATs, and a
translation unit compiled without `/Gy` emits none.** This image has at least
one such TU. So "identical bodies at two addresses" is evidence about how one
of them was COMPILED, not about whether the linker folds; only the positive
observation (one address in many vtable slots) tells you ICF is on.

## An inlined callee's temporary lives in a dead parameter slot

`ILTStream::GetPos()` and `GetLen()` are inline helpers in `iltstream.h`;
each declares its own `unsigned long` and takes its address. When VC6 inlines
them it does not grow the frame — it puts that temporary in a PARAMETER home
slot whose parameter is already cached in a register. Two functions in
`lttexmod.cpp` pass `&[esp+arg1]`, `&[esp+arg3]` and `&[esp+arg5]` having
cached those three parameters in esi, ebp and ebx; `0x0041ff90` does it with
its own second parameter.

Read without knowing this, such a frame looks like source that assigns to its
own parameters. It does not. This is the same slot-reuse as "dead parameter
slots host locals", one step further out: the local need not even appear in
the source being read.

## A virtual called on a global OBJECT devirtualises; the shipped code uses a pointer

`g_ConsoleHistory.FindFirst(LTNULL)` — a virtual invoked on an object rather
than through a pointer or reference — lets VC6 bind statically, and it emits
a direct `call`. The shipped build keeps the dispatch while folding `this` to
an immediate:

	mov 0x4b2ec4,%eax        ; the object's vptr, loaded from its first dword
	mov $0x4b2ec4,%ecx       ; this, as a compile-time immediate
	call *0x14(%eax)         ; slot 0x14

That pair — vptr loaded from a fixed address, `this` as an immediate, and an
indirect call — is what a compile-time-known POINTER to a polymorphic object
gives. Introducing `CConsoleHistory* pHist = &g_ConsoleHistory;` and calling
through it closed `cc_ListHistory`.

The tell: ours is SHORTER than the shipped body and the differences are
`call X` where the shipped has `mov <global>,%reg` + `call *N(%reg)`. Do not
confuse it with the peeled-loop tell below, where the duplicated
instructions are the loop CONDITION rather than the dispatch. Note also that
a direct call is not automatically wrong — several functions in the same file
call methods on globals and match, because those methods are not virtual.

## An empty-bodied `while` gets its first iteration peeled

`while (::ShowCursor(TRUE) < 0) ;` — a spin loop whose whole body is the
condition's side effect — comes out of VC6 /O2 as a pre-test plus a rotated
loop, i.e. the condition is emitted TWICE:

	    push $1; call *%esi; test %eax,%eax; jge out
	top: push $1; call *%esi; test %eax,%eax; jl  top
	out:

The shipped build tests once, at the bottom:

	top: push $1; call *%esi; test %eax,%eax; jl top

which is what `do ; while (::ShowCursor(TRUE) < 0);` gives. Two functions in
`cltcursor.cpp` were 80 bytes against 53 and 64 against 53 for this reason
alone, and both closed to byte-identical on the change — that TU went from 11
matched with 2 unmatched to 13 with none.

The rule generalises past spin loops, and it runs in BOTH directions. What
the shipped build tells you is where its ONE copy of the condition sits; a
duplicated condition in ours means the loop form in the source is wrong, not
that `do`/`while` is always the answer:

  * `cltcursor.cpp`'s spin loops needed `while` -> `do`/`while` (the test
    belongs at the bottom), 80 bytes down to 53.
  * `clientconsole.cpp`'s `CConsoleNameList::FindNext`/`FindPrev` needed the
    opposite. Written as `do { if (!Next()) break; ... } while (!bFound);`
    VC6 duplicated the `Next()` call and both came out 110 bytes against 96;
    hoisting the test to `while (!bFound) { if (!Next()) break; ... }` closed
    both. A `do`/`while` carrying `break`s is the shape that provokes it.

So the tell is the duplicated condition, and the fix is to try the other loop
form. Check this before reading registers: it is one edit, and it moved four
functions.

One thing it is NOT: a duplicated *call* is not always a peeled loop.
`cc_ListHistory` also came out short of the shipped size with call-shaped
differences, and there the cause was that the shipped code calls a virtual
through a global POINTER (`mov <global>,%eax; call *N(%eax)`) where ours
calls a method directly. Read whether the extra instructions are the
condition or the dispatch.

## The pad that forgot the vptr

A layout-identical view class written as

	class CFooView {
	public:
		virtual void _v00() = 0;
		uint8  m_pad_000[0x34];
		void*  m_p034;                // +0x34
	};

puts `m_p034` at 0x38, not 0x34, because the vptr occupies 0x00 and the pad
starts after it. Every field below it is then four bytes high, and the whole
class compiles, links and looks right. The tell is uniform and one-directional
in `nearpos.py` output — `+11:38->34`, `+14:3c->38` — never a register
difference. The pad on a polymorphic class has to be written as an arithmetic
difference (`[0x34 - 0x04]`) so it cannot drift.

The same shape appears with a field genuinely missing rather than mis-padded,
and then the deltas run the other way: `CClientMgrView` had nothing declared
at +0x508, so every offset below came out four bytes LOW (`+6:d4->d8`).
Restoring the field took that TU from 13 matched to 19 in a single build.
Whenever several unmatched functions in one TU show the same delta in the same
direction, stop reading codegen and go count the class.

## The dividing line: ORDERING is source-reachable, ALLOCATION is not

Eight attempts at size-exact near-misses on lithtech.exe, five conversions and
three failures, and they separate cleanly along one line. Check which side a
residual falls on before spending a build.

**SOURCE-REACHABLE -- ordering.** Every conversion was one of these:

  * statement order (`CLTClient::OpenFile`: put the success return on the
    fall-through so the error block hosts after it);
  * member-store order (`TCPQueryResponse`: +0x98 before +0x9c;
    `CObjPolyGrid`: m_f1d8, then ten zero stores, then m_f1d4 last);
  * comparison operand order (`FindBySegState`);
  * where a cast sits (`sub_42f220`: narrowing inside the macro, not outside).

**NOT SOURCE-REACHABLE -- register and slot allocation.** Each of these was
tried and the emitted bytes came back byte-identical to before:

  * which operand of an address computation becomes base and which index --
    `lea X(%esi,%eax,1)` vs `lea X(%eax,%esi,1)` (`ResetRecords`); `+` is
    commutative and the order is gone before allocation runs;
  * which register holds an inlined vtable load -- `mov (%ecx),%edx` against
    `mov (%ecx),%eax` (`cs_ReleaseListItems`);
  * WHICH stack slot a given scalar gets when the frame size already matches.
    `fs_AddResources` differs only in one local sitting at 0x24 rather than
    0x1c, and reordering the declarations -- including hoisting the inner-scope
    walk variables ahead of it -- changed nothing at all.

**Frame SIZE is NOT reliable evidence either, and the example that suggested it
was is the one that disproves it.** `sav_SaveObjects` (0x00431770, 842 bytes)
is instruction-for-instruction identical to the shipped function -- 288 of 288
-- and differs in ten instructions: the frame (`sub $0xec` against our
`sub $0xe8`), the two parameter reads that shift with it, and a four-way
permutation of the slots holding `nTrees`, `pBsp` and `nChunks`.

Two hypotheses tested, both negative:

  * *A local is missing.* No: enumerating every `esp`-relative access on both
    sides gives **exactly the same eleven slots**. The shipped function's extra
    four bytes are never read and never written. A source variable that is
    never accessed does not get emitted, so there is nothing to add.
  * *Lexical scope controls slot sharing*, so declaring the inner-scope
    variables at function scope would stop them sharing and grow the frame. No:
    hoisting `nTrees`, `iChunk` and `pBsp` to function scope changed nothing at
    all. **MSVC allocates by live range, not by scope**, which is worth knowing
    on its own -- moving a declaration in or out of a block is not a lever.

So a frame that differs by a few bytes with the same slots touched is reserved
space the allocator did not use, and belongs on the NOT-source-reachable side
with the rest. Only a frame difference accompanied by a slot the shipped
function touches and ours does not is worth chasing.

## `lea X(%esi,%eax,1)` vs `lea X(%eax,%esi,1)`: allocation, not source

A near-miss whose only residual is the base and index of a `lea` swapped is
**not reachable from the source**. `ResetRecords` (lithtech.exe 0x00413cf0,
42 bytes) differs from the shipped function in exactly one instruction --
shipped `lea X(%esi,%eax,1)`, ours `lea X(%eax,%esi,1)` -- and writing the
addition the other way round (`nOffset + pBase` for `pBase + nOffset`) changes
nothing: the emitted bytes are identical before and after.

Which operand becomes the base and which the index falls out of register
allocation, and `+` is commutative so the front end has already discarded the
order by the time it matters. Contrast the genuinely source-visible cases,
both confirmed by conversion:

  * **`cmp X(%eax),%ecx` vs `cmp %ecx,X(%eax)`** -- comparison operand order
    DOES survive. `CDMPlayingListView::FindBySegState` converted to
    byte-identical by rewriting `pNode->m_pSegState == pSegState` as
    `pSegState == pNode->m_pSegState`.
  * **Adjacent member stores** -- declaration and statement order survive.
    `TCPQueryResponse::TCPQueryResponse` converted by writing `m_pData`
    (+0x98) before `m_Unknown9c` (+0x9c), matching the shipped store order.

So: operand order of a COMPARISON is evidence; operand order of an ADDITION
inside an address is not. Do not spend a build on the latter.

## The inliner is forward-only, and `inline` is what admits a big helper

Two facts about VC6 that only show up in an image built at `/O2`, and that
together are worth more than any single function:

**1. A function defined BELOW its caller is not an inlining candidate.**
Not at `/O2`, not with `/Ob2` (measured and refuted separately). Source order
decides candidacy, so a helper at the bottom of a translation unit is expanded
nowhere in it and a helper at the top is expanded everywhere.

**2. `inline` raises the size limit; hoisting alone does not.** A 234-byte
helper is far past what VC6 will take unbidden. Moving `sm_SetObjectChangeFlag`
above its fourteen callers changed NOTHING -- byte-identical output to before.
Adding `inline` as well took a probe from 1 match to 10, and the real edit in
`servermodel.cpp` gained lithtech.exe eight functions. `inline` does not
suppress the standalone out-of-line copy when the address is taken, so the
shipped image legitimately has both: one COMDAT at 0x00469b80 AND an expansion
inside every caller.

**How to recognise it.** Our function is a large fraction shorter than the
shipped one -- 123 against 346, 24 against 155 -- and the missing bytes are
close to the size of a helper it calls exactly once. Check whether that helper
is defined after the caller in the same file. If it is, hoist it and mark it
`inline`, then re-verify BOTH images.

**Why it hid for so long.** `/O1` does not inline at all, so `server.dll` --
the oracle for every shared translation unit until now -- cannot show this
class of defect. See the companion rule: for shared TUs, fix shape against
`lithtech.exe` (/O2) and re-verify against `server.dll` (/O1), never the
reverse. `serverengine.cpp` alone matched 19 of 23 in server.dll against 11 of
23 in lithtech.exe from the same source, and that gap is where this lives.

### Marking a function `inline` can COST you that function's own match

The companion hazard to the forward-only inliner, and it is easy to miss
because it shows up in the OTHER image from the one you are working on.

`inline` does not suppress an out-of-line copy when the address is taken --
but when the address is NOT taken and every caller expands it, the COMDAT
stops being emitted. In `server.dll` (`/O1` = `/Os`) the helper is still
called out of line, so its standalone body is a real function in the shipped
image and one of our objects was matching it. Mark it `inline` to fix
`lithtech.exe`, and if `/Os` now expands it too, that server.dll match is
gone.

So **every `inline` is a bet that must be measured on BOTH images
separately**. Three of them from one file:

    CWorldTable::SetSizeInit2   server -2, lithtech +0   -> REVERTED
    ModelWalker::ModelWalker    server  0, lithtech +1   -> kept
    CConnList::AllocItems/FreeItems (24b/32b)
                                server -2, lithtech -1   -> REVERTED

The last pair also bounds the `/Os` inline budget from below: at 24 and 32
bytes `/Os` DOES expand, so the threshold that separates the two builds sits
above 32 bytes, not below. Anything smaller than that is not a candidate for
this technique at all -- both builds will expand it and the spelling cannot
be what distinguishes them.

Practical rule: apply one `inline` at a time, rebuild BOTH targets, and keep
it only if `lithtech` gains at least as much as `server` loses. A helper that
is "expanded in /O2, called in /O1" is the right shape; a
helper whose own standalone body is currently matching in server.dll is the
one to be careful with.

### The inline decision is CALLER-CONTEXT-DEPENDENT, not a property of the callee

This is the rule that bounds the whole inline-visibility technique, and it was
learned from a batch of header edits that mostly could not work.

VC6 at `/O2 /Ob1` decides expansion per CALL SITE, not per function. The same
helper, in the same image, from the same header, is expanded at one site and
called at another:

    LTMatrix::Init (114b)              EXPANDED in mat_SetupTransform (196b)
                                       CALLED   in GetNodeTransform (1182b)
    Mat_InverseTransformation (147b)   EXPANDED in wm_BuildTransforms
                                       CALLED   in sub_10017517
    MatVMul_3x3 (83b)                  never expanded anywhere
                                       -- though LARGER helpers often are

Depth alone, callee size alone, and source order alone each fail on at least
one of those. So a header keyword cannot separate two call sites of the same
function, and any header-level change is all-or-nothing across every caller.

**The check before betting a keyword on an over-inline:** grep the whole
shipped image for calls to the helper's address. If ANY currently-matching
function expands it, a header-level suppression is a guaranteed loss. The
ltmatrix case had exactly this shape -- `wm_BuildTransforms` matches at
0x004342b0 (718 bytes) with `operator~` fully expanded, while `sub_10017517`
needs it called, from one header. No source change confined to that header can
separate them, so the correct action was to make no change.

**Where the lever actually is: the CALL SITE.** If the shipped bytes want a
helper called where we expand it, look at how the caller's source spells the
expression. `LTMatrix mRel = (~A) * B;` and
`LTMatrix mInv = ~A; LTMatrix mRel = mInv * B;` are the same computation and
need not compile alike -- the shipped bytes for the second copy the NRV temp
into a second slot before MatMul reads it. That is a `.cpp` edit, in ORDERING
territory, and it is source-reachable where the header is not.

## Two rules that do NOT hold everywhere -- check before applying

Both are easy to state as general rules, and both were refuted by measurement
in `src/engine/server/worldsim.cpp`.

**The float-product operand rule is not universal.** The rule says VC6 `fld`s
the RIGHT operand and folds the left into the `fmul`, so `fld A ; fmul B`
means the source wrote `B * A`. That is proven on `LTMatrix::SetupRot`. But at
0x10004986 the shipped code is `fld vDir.x ; fmul fRemaining` and **our object
already matches it from `vScaled.x = vDir.x * fRemaining`** -- i.e. `A * B`,
the other way round. Three instances in that TU agree. **Verify the rule
against a byte-identical site in the SAME function before using it to argue
about operand order.**

**`/Oy` does not mean frameless.** The rider that scalars sit at the low end
of an `esp` frame with aggregates above assumes there is no frame pointer.
All three of worldsim's big simulation functions open `push ebp ; mov ebp,esp`
**despite `/Oy`**, so they are `ebp`-relative and the ordinary rule applies
instead. Check the prologue before reasoning about slot order.

## A three-float store through `fld`/`fstp` is `_CVector<T>::Init`

Member assignment of a float gives an INTEGER move -- proven in-tree at
0x10002a37, where `vOnPlane.y = m_fMin` already matches byte for byte. So a
run of three `fld`/`fstp` pairs writing x, y and z is NOT three assignments;
it is `ltvector.h:31`'s `Init(x, y, z)` inlined, and the giveaway is a `lea`
of the inlined `this` dropped into the run with no call to explain it
(0x10002e38 has exactly that, followed by three `fldz`/`fstp [eax+N]` --
2/3/3 bytes rather than three 6-byte absolute stores).

Ruled out by measurement: `VEC_SET` explains the `fld`/`fstp` but not the base
pointer or the reversed argument evaluation; `VEC_INIT` is excluded outright,
because a chained assignment stores z,y,x with one `fldz` where shipped stores
x,y,z with three.

## The frame-growth direction is NOT constant, and two of this guide's own examples are on opposite sides

The rule above says locals bump DOWN in declaration order. Five functions
from one cl-8447 `/O1` build split two ways:

    down: w_IsectObjectGeometry, SetupRotationAroundPoint
    up:   w_ReadWorldLights (byte-identical, 23 locals, the uint16 hole
          visible), AlignRotation (byte-identical), wm_UpdateDimsFromGeometry

It is not the translation unit -- servermath supplies one of each -- not the
compiler revision, and not whether an address is taken. **Two of the five are
byte-identical, so the direction is observable rather than inferred.**

This matters more than a curiosity: **the two specimens this guide names are
exactly the two remaining nears whose entire residual is frame
displacements.** So the rule as written may be circular -- fitted to the two
functions it cites. Anyone reasoning about declaration order from slot order
should first establish which way THAT function's frame grows, using a
byte-identical neighbour in the same TU if one exists.

`w_GetPointShade` is the current worked example. Its declaration order was
derived from BOTH images' frames at once, and exactly one grouping reproduces
them -- splitting the eight corners 4+4, or the two plane samples into
separate statements, or the three blend temporaries into three, each breaks
the client's frame. Three independent agreements. The body still comes out
1024 against 1047 with every residual a frame-slot SIGN (shipped negative off
`ebp`, ours positive), which is this same direction question and not the
declaration order.


## Operand order on a vector operator is a TWELVE-BYTE FACT, not allocation

`_CVector<T>::operator+`, `operator-`, `operator*` and `Dot` take their right
operand **by value** (NOLF1's `ltvector.h`; NOLF2's is `src/Engine/sdk/inc/ltvector.h`). So in `a + b` the RIGHT side
gets a twelve-byte stack copy and the LEFT is read straight out of the object
as `this`.

That makes the two spellings visibly different, and the difference is worth a
whole vector of frame per site:

    shipped:  fadds 0x18c(%esi)              <- the member is the LEFT operand
    ours:     movsl ; movsl ; movsl          <- the member is the RIGHT operand
              fadds -X(%ebp)

So when a shipped function reads a member in place with `fadds`/`fsubs` off
the object and ours copies twelve bytes into a temporary first, do not write
it off as register allocation: **swap the operands**. The frame moves by
exactly 0xc per site, which is how to check the arithmetic before building.

Worked examples, same file: `wm_RotatePushObject` (0x10020e31) went from
799 bytes to 811 against a shipped 811 -- size AND instruction exact,
276/276 -- on this rule plus one member re-read. `wm_PushWithGeometry`
(0x1001f5cd) went 994 to 990 against 991, five mnemonic blocks.

The same rule read backwards is how to tell which operand the source named
first when only one side is a member: count the twelve-byte copies. Both
images agreed at every site tested, so it is not an optimisation-level
artefact.

CAVEAT, because one of the three sites did not behave: at `wm_PushWithBox`
(0x1001fb22) the swap takes the mnemonic diff from 9 blocks to 8 but the
instruction count from 381 to 377 against a shipped 391 -- further UNDER. The
rule is applied there for consistency, but that function has an unexplained
x87 spill in its two NOSLIDING arms, so do not read its numbers as support.


## `/Ob1` expands only `inline` and in-class. Position is the SECOND condition.

The forward-only inliner is real and this guide records it elsewhere -- VC6
cannot expand a function defined below its call sites. But that is not the
first thing to check, and treating it as the first thing wastes a
measurement.

`sav_WriteVector` in `savobj.cpp` was `static`, declared above its two callers
and defined two hundred lines below them. The shipped lithtech.exe expands
both sites and emits no out-of-line body at all. Moving the definition above
the callers changed NOTHING: 1199 bytes before, 1199 after.

`/Ob1` is "expand only functions marked `inline`/`__inline` or defined inside
a class body". A plain `static` free function does not qualify no matter where
it sits. Adding `inline` took the caller from 1199 to 1240 against a shipped
1238, and to 447 instructions against 447.

So the order to check is:

  1. is the callee marked `inline`, or defined in-class? If not, `/Ob1` will
     never expand it and nothing about position matters;
  2. only then, is it visible above its callers?

Both conditions have to hold. The in-class form is the one to reach for on a
member (`GetSpaceLeft` in `netmgr.cpp`: lithtech 949 -> 971 while
server stayed at 766, because /Ot accepts the body and /Os declines it -- one
spelling, both images, which is the oracle working).


## The mixed-compiler theory for the size-exact nears: tested, rejected

(NOLF1 history: NOLF2 is one revision throughout. Kept because the
measurement is the lesson: a plausible compiler explanation was tested and
lost.)

server.dll's Rich header really is a mixed build -- 95 C++ objects from cl
8447 and **8 from cl 8168** (plus 146 C objects from 8168, which are library).
`build/env.sh` carries a `CL_REV=` override precisely so this can be tried, and
`fndiff`'s own closing hint suggests it whenever a function is size-exact with
few residual blocks.

It is a good theory and it is wrong for our translation units. Measured on the
four best candidates -- the objects whose nears are most heavily size-exact --
building with 8168 instead of 8447 gives:

    objbank        8447 = 101   8168 = 101
    servermessage  8447 = 101   8168 = 100
    serverengine   8447 =  25   8168 =  25
    collection     8447 = 457   8168 = 457
    lmessage       8447 =  34   8168 =  34

Equal or WORSE in every case. Whatever those eight 8168 C++ objects are, they
are not translation units we have reconstructed. Do not spend another sweep on
this without new evidence -- and if you do find evidence, note that the
size-exact nears are spread across TWENTY-SIX objects, which is already hard to
square with eight.


## What the size-exact nears actually are, and why source work will not move them

When server.dll still had about a hundred nears, more than half of them were
SIZE-EXACT and four in five were within four bytes. Of twelve size-exact ones
sampled, TEN differed only in register or frame-slot choice, with a median of
two mnemonic blocks.

The recurring shapes, all catalogued and none source-reachable:

  * frame-slot SIGN -- ours at `X(%ebp)` where the shipped build is `-X(%ebp)`;
  * COUNTER HOMING -- the shipped build keeps a loop counter in a dead
    parameter home slot and increments it in memory, ours enregisters it;
  * which register holds `this` (`%ebx` against `%ebp` is the common pair);
  * scale-1 SIB base/index order (`X(%ecx,%eax,1)` against `X(%eax,%ecx,1)`),
    already a recorded negative here and in
    [10-upgrading-nears](10-upgrading-nears.md).

One shape in that sample WAS source-reachable and is worth knowing: at
lmsg_AfterRead (0x10014cf8) the shipped build loads the two members in the
opposite order to ours before subtracting them, computing the same value with
the registers swapped. That is operand-evaluation order, and hoisting one
operand into a local is the lever ([12-o2-shape](12-o2-shape.md)).

The practical conclusion: the near bucket is close to exhausted by source-level
work -- though see the last section for the levers that did close some.
Effort is usually better spent on the `attempted` bucket, where functions are
unwritten or far off and source work still pays: four written together landed
at 1010/1010, 1025/1025, 696/695 and 1096/1090.


## Dead-parameter-slot homing must be checked against BOTH images

The shipped build often keeps a value in a dead incoming-parameter slot where
ours uses a fresh local, and reproducing that placement looks like a clean
source-level win. It is usually not one, and here is the case that proves it.

In `sub_10022c2f` (netmgr, 0x10022c2f), passing `&pData` to `msg_AllocPacket`
reproduces the shipped /O1 frame map EXACTLY and takes server.dll from 308 to
311 of 317 bytes. Convincing on one image.

lithtech.exe kills it. At /O2 the message goes into *pConn's* slot
(`lea 0x48(%esp)` at 0x004581e1) while the payload base is read from pData's
own slot at 0x00458266. **Two images, two different dead parameter slots, one
source** -- so the slot is allocator leftover, not something the source
chooses. The /O1-only rewrite costs the client image four bytes.

So: a frame-placement change that agrees with one image and is silent about
the other has not been tested. The two-image oracle is the whole point, and
this is the shape most likely to fool it.

## Levers that closed "register allocation" verdicts

A sweep of 60 server.dll nears, almost all previously filed as allocation,
scheduling or compiler-revision residue, closed 26 of them. Every one of
these was a source difference; none was the compiler's whim.

* **Which pointer variable the uses go through decides add operand order.**
  VC6's strength-reduced `base + offset` add takes its operands in opposite
  orders for a local pointer copy (`pWorld = this`, `pGeom = pData`) and for
  the original. Adding a copy closed `CWorldSimple::Load`; removing one closed
  `wm_ResetGeometry`. Dropping a user local and reading the member chain at
  both uses also flipped a SIB base/index order (`GetNumFrames`) -- so SIB
  order is NOT always a dead end.
* **Stores whose values are all live in registers before the first store are
  the arguments of an inlined helper.** `UpdateAttachments` and
  `sav_RestoreObject` (after all 720 statement orders had been built) closed by
  filling the struct through a `wm_InitMoveState`-style inline.
* **A field loaded after a neighbouring store in shipped but before it in ours:
  read it through a pointer to the field** (`uint8** pp = &pMsg->m_pData;`).
  Closed `GetPacket`, `WriteAckPacket`, `AddSentBytes`.
* **Callee-saved push placement follows single-exit regions.** VC6 saves a
  register around the smallest single-exit region holding its variable; early
  returns inside it drag the push to entry. Nested positive tests with one
  shared return moved it (`SetObjectFlags`).
* **Dead-parameter-slot homing is source-reachable**: statement order decided
  which local took the slot (`w_FindPolyAtPoint`: `pNode = ...` before
  `nIndex = 0xffff`); block scope did elsewhere (`sav_SaveObjects`' nTrees).
* **"movzx elision only our cl revision does" was wrong.** Writing the select as
  an if / else-if / else chain instead of a hand-written shift and mask keeps
  the `movzbl` (`si_GetObjectState`); a header member of the wrong width
  (uint8 where lithtech loads a dword then `and $0xff`) was the rest.
* **A macro's parentheses are part of the source.** `LTMIN(r, C)` expands to
  `(r) < C ? ...`; the parentheses round the compare's LEFT operand give
  `flds C; flds r; fcomp %st(1)`. Without them r folds into `fcoms mem`.
* **A callee's parameter width shows at the CALLER.** A word writer that reads
  only the low word compiles identically with a uint32 parameter, but the
  caller then pushes the dword whole, as shipped does.
* **Inline budget.** VC6 caps inline expansions per function and refuses the
  EARLIEST sites once over. A shipped CALL where we inline (AddAfter in
  sm_AddClientForConnection) can mean the original expanded ~15 more inlines
  earlier in the function. Padding reproduces it; the real ones are unknown.
* **A header symbol-count threshold.** tcpdriver.cpp's `HandleConnPacket` flips
  on ANY added declaration in lthread.h/servermgr.h, used or not. Count
  declarations when a header change costs it; removing dead ones compensates.
* **Loop shape from returns inside the loop.** `if (++j >= 8) return 1;` gives
  the shipped `cmp; jae <return>; jmp top` tail; `for (j...)` never rotates.
* **`*(volatile float*)&x` at one read site** forces the store+reload shipped
  shows (`w_PointInPoly`).
