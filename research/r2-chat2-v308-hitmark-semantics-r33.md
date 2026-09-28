# Chat 2 — exact-v308 hitmark semantics R33

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R33 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or any earlier R3-R32 candidate batch.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_79333AA52A38368370D8`
- field/method proposals: **0**

## `rs/a/e` -> `HitmarkManager`

Every R30 `Actor` creates one `rs/a/e` object and delegates hit insertion/update into
it. The class owns:

- exactly four active `rs/a/f` slots;
- an overflow/replay `CopyOnWriteArrayList<rs.a.f>`;
- cycle-based slot expiry/replacement;
- reset/clear behavior;
- active-slot checks used by the client renderer.

When all four slots are occupied, optional overflow records are retained and retried as
slots expire.

The exact client terminology removes the main naming ambiguity that remained at R32:
the client loads these assets from literal `hitmarks/...` paths and the config framework
contains the key `hitMarkStyle` labelled `Hitsplats`.

Because the record noun surviving in the client is **hitmark**, the Actor-owned lifecycle
container is proposed as `HitmarkManager`.

## `rs/a/f` -> `Hitmark`

Each active manager slot is one `rs/a/f` record. The manager constructs it from the
incoming hit style/type, displayed damage/value and auxiliary icon information, then sets
screen offset/duration and an expiry cycle.

The client invokes the record directly during Actor overhead rendering. Its render paths
select the client's old/new hitmark sprite families and draw the numeric damage value.

Exact surviving resource names include:

- `hitmarks/old/hit`
- `hitmarks/old/crit`
- `hitmarks/old/heal`
- `hitmarks/old/block`
- `hitmarks/old/poison`
- `hitmarks/old/venom`
- `hitmarks/new/block`
- `hitmarks/new/hit N`
- `hitmarks/new/icon N`

That makes `Hitmark` preferable to the otherwise plausible `Hitsplat`: the latter appears
as user-facing config wording, while `hitMarkStyle` and the asset namespace preserve the
client's implementation noun.

## Still withheld: `rs/a/d`

R33 does not name `rs/a/d`.

It is a compact three-integer-per-entry storage object used by Model and the model-data
provider, with get/set/add operations for each component. The behavior is compatible with
a packed vector/normal accumulator, but the exact semantic noun is still not uniquely fixed
by v308 evidence. It remains unnamed rather than converting resemblance into authority.

## Acceptance boundary

Chat 2 does not promote R33. Main/Core may accept either or both proposals only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_79333AA52A38368370D8`.
