# Chat 2 — exact-v308 semantic frontier triage after R275

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

This note supersedes the narrower after-R265 frontier note where later retained reviews have
already resolved adjacent classes. It records exact-v308 targets that remain intentionally
unnamed after the retained R273-R275 expansion, so future Chat 2 continuations do not turn
weak shape evidence into semantic authority.

## Clean checkpoint

- latest retained semantic batch: **R275**;
- R275 head: `feb082374f8ee90349e9b3853292759c1538228d`;
- Recovery CI `36294132389`: Ubuntu + Windows **success**;
- PR #9 remains Draft, mergeable and 0 behind current Main at this checkpoint.

## `rs/a/d` — packed three-int entry store

R33 deliberately withholds this class.

Exact behavior already established in the retained R33 evidence:

- compact three-integer-per-entry storage;
- used by `Model` and the model-data provider;
- get/set/add operations for each component.

That shape is compatible with several vector/normal accumulator roles, but no surviving
literal, source fingerprint or uniquely identifying consumer fixes one exact noun.

**Decision:** keep unnamed.

## `rs/gui/b/f` — loadout item-id/quantity pair

R143 deliberately withholds this class.

Exact behavior already established in the retained R143 evidence:

- two integer fields;
- used by Loadouts inventory/equipment state;
- one value represents item id and the other quantity.

The surrounding subsystem is unquestionably Loadouts, but the class itself does not preserve
a narrower original noun. Names such as `ItemStack`, `LoadoutItem`, or `ItemAmount` would
currently be conventions rather than recovered identity.

**Decision:** keep unnamed until direct source provenance or a surviving self-identity fixes the noun.

## `rs/z/c` — cooldown boolean predicate

R252 deliberately withholds this interface.

Exact behavior already established:

- one boolean-returning method;
- referenced only through a protected field on reviewed `CooldownTimer`;
- no exact-v308 behavioral consumer establishes the predicate's specific role.

The timer hierarchy itself is recovered, but the interface noun is not.

**Decision:** keep unnamed.

## `rs/l/e/i`, `rs/l/e/l`, `rs/l/e/m` — render callback / scrolling text holdouts

The after-R265 exact-bytecode audit remains authoritative here.

- `rs/l/e/i`: one method `void a(rs.n.e, int, int)`; callback/render role is proven,
  source noun is not.
- `rs/l/e/l`: tiny mutable String + x/y record, initialized around the client text viewport.
- `rs/l/e/m`: current-record + FIFO queue manager; measures text width, decrements x,
  draws white text and advances queued records.

No surviving exact-v308 producer invokes the enqueue method, so the originating feature noun
is still absent.

**Decision:** mechanics are known; semantic names remain withheld.

## Compiler / empty-shell exclusions

The previous exact audit remains valid for:

- `rs/runelite/a/k`, `rs/runelite/a/n`: empty package-private shells;
- `rs/l/f/d`, `rs/l/f/h`, `rs/l/f/k`, `rs/l/f/n`: enum switch-map helpers;
- `rs/ui/components/h`: empty package-private shell;
- `rs/ui/components/t`: enum switch-map helper;
- `rs/ui/i`: enum switch-map helper;
- `rs/s/t/k`: Trading Post enum switch-map helper.

These do not receive semantic proposals.

## ScriptPacket 32 — mixed-domain handler

`rs/q/a/a/a/a` remains intentionally unnamed.

Earlier exact reviews established that individual selectors touch recognisable surfaces,
including Blood/Infernal spell widget names/sprites, but the class as a whole also mutates
unrelated Client state, strings and toggles. No single subsystem noun describes the complete
selector surface honestly.

Later ScriptPacket work does not change that whole-class coherence rule.

**Decision:** keep unnamed unless a stronger whole-class identity is recovered.

## Boundary

This is negative research evidence only.

- no R276 semantic candidate is created from these holdouts;
- no canonical state is changed;
- no semantic acceptance is performed;
- future work should widen to new exact-v308 nested/interface/source-fingerprint families rather
  than revisit these targets without new evidence.
