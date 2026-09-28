# Chat 2 — exact-v308 legacy item description appender R105

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R105 is a separate non-canonical class-only review for the live hardcoded item-description
helper used by the client item display/hover path.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_8801B19E494743EB89A1`
- field/method proposals: **0**
- confidence: **0.997**

## Stable ID

- `rs/q` -> `CLIENT_CLASS_000742` -> `LegacyItemDescriptionAppender`

## Exact transform contract

The class has one relevant static method:

`String a(String)`

It accepts an existing item display string and checks it against a hardcoded SpawnPK item
table.

Recognized names append multi-line lore/effect text to the original value.

Surviving examples include:

- `Killer's dagger`;
- `Adventurer's whip`;
- `Blood key`;
- seasonal boost/doubler/hotspot scrolls;
- `holy shard` / `shard of balance`;
- `summer totem`;
- bloodlust and event consumables.

The appended text preserves exact client formatting tokens such as:

- `@yel@`;
- `@gre@`;
- `@or1@`;
- `@whi@`;
- embedded `<img=...>` tags;
- explicit line breaks.

Unknown item names are returned unchanged.

## Exact live consumer

`Client.a(int, String, boolean)` is the live item display path.

It resolves the ItemDefinition, builds the item display string, then in the boolean detail
mode directly invokes:

`rs/q.a(String)`

on that item display text.

The result is used as the displayed item text.

The same path also calls R72 `ItemHoverDescriptionConfig`, which provides the newer
config-driven description mechanism.

This relationship fixes `rs/q` as the legacy hardcoded description appender rather than
a generic String utility.

## Deliberate exclusion: `rs/r`

The adjacent `rs/r` class has an obvious hardcoded reward-preview renderer:

- it matches promo/event item names;
- builds arrays of reward item IDs;
- directly calls a Client render method with description text and those IDs.

However, an exact classfile reference scan finds **no surviving caller** for
`rs/r.a(String)` in v308.

R105 therefore does not name it. A role can be inferred from its own body, but the current
Chat 2 evidence standard requires more than a dead/orphan utility body when a live-call
identity is unavailable.

## Naming boundary

No surviving original source noun was found for `rs/q`.

`LegacyItemDescriptionAppender` is deliberately descriptive. Confidence is 0.997 rather
than 0.999.

## Acceptance boundary

Chat 2 does not promote R105. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_8801B19E494743EB89A1`.
