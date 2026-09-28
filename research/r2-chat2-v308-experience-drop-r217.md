# Chat 2 — exact-v308 experience-drop presentation R217

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R217 is a separate non-canonical class-only review for the exact skill-experience drop
record and its live queue/render manager.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_CBA61CC93BAF1D34A929`
- field/method proposals: **0**

## Stable IDs

- `rs/l/e/d` -> `CLIENT_CLASS_000424` -> `ExperienceDropEntry`
- `rs/l/e/e` -> `CLIENT_CLASS_000425` -> `ExperienceDropManager`

The IDs continue the canonical exact-v308 sorted `rs/**.class` seed-lineage order used by
the prior Chat 2 batches.

## ExperienceDropEntry

`rs/l/e/d` is referenced only by the manager.

One instance stores:

- one accumulated numeric amount;
- a `List<Integer>` of contributing skill ids;
- x/y-style presentation offsets;
- alpha/fade state;
- one fade-phase boolean.

The constructor receives an amount plus one skill id and seeds the skill-id list with that
single id.

When the manager combines compatible rapid gains it adds the new amount to this record and
adds the new skill id only when it is not already present.

That fixes the value as one potentially combined experience-drop entry rather than a generic
animation record.

## ExperienceDropManager

The constructor allocates exactly **23** skill sprites and loads each from:

`skills/<id>`

Each image is resized to **13x13**.

### Exact live skill-update input

The Client skill-update path invokes:

`rs/l/e/e.a(skillIndex, newValue - oldValue)`

only when the incoming delta is positive.

The manager rejects negative skill ids and zero amounts before constructing a drop.

This directly links its public input to positive per-skill experience gains.

### Combination and queueing

The manager creates one `ExperienceDropEntry` per accepted gain.

For skill ids in the exact set `0, 1, 2, 4, 6`, and also for skill id **3**, a gain arriving
within **650 ms** can merge into the most recent active entry:

- the amount is accumulated;
- a previously absent skill id is appended to the entry.

When active entries are still too close vertically, a new entry is queued rather than drawn
on top of them. Queued entries are promoted once spacing permits.

### Render lifecycle

For every active entry the manager:

1. formats the amount with an exact leading `+`;
2. uses the client's compact numeric formatter once the amount reaches five digits;
3. renders each contributing `skills/<id>` icon when the relevant gameframe surface is
   visible;
4. renders the amount beside those icons;
5. advances vertical/fade state;
6. stages and removes entries after their fade completes.

The active/queued ownership plus combination, animation, rendering and removal surface makes
this a manager rather than one overlay value.

## Naming boundary

No surviving source identifier proves an original class name.

`ExperienceDropEntry` and `ExperienceDropManager` are descriptive exact-behavior recovery,
both at confidence **0.999**. The review deliberately uses “Experience” rather than assuming
that the stripped source used the abbreviation “XP”.

R217 adds no field or method proposals.

## Acceptance boundary

Chat 2 does not promote R217. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_CBA61CC93BAF1D34A929`.
