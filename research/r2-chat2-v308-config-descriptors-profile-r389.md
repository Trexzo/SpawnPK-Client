# Chat 2 — exact-v308 config descriptors/profile R389

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/e/h` -> `CLIENT_CLASS_000152` -> `ConfigItemDescriptor`
- `rs/e/k` -> `CLIENT_CLASS_000155` -> `ConfigProfile`
- `rs/e/m` -> `CLIENT_CLASS_000157` -> `ConfigSectionDescriptor`
- review: `SEMREVIEW_7366B9C7005BFA7E1925`

These names are unusually strong because exact v308 preserves all three directly in
self-identifying `toString()` templates.

## ConfigItemDescriptor

Exact template:

`ConfigItemDescriptor(item=..., type=..., range=..., alpha=..., units=...)`

The object stores the R16 `ConfigItem` annotation, Java return Type, `Range`, `Alpha`
and `Units`. It implements the common R16 `ConfigObject` contract by forwarding
name/description/position to the item metadata.

## ConfigProfile

Exact template:

`ConfigProfile(id=..., name=..., sync=..., active=..., rev=...)`

The five fields match that template exactly: long id, String name, sync flag, active flag,
and revision long. A helper additionally tests whether the profile name begins with '$'.

## ConfigSectionDescriptor

Exact template:

`ConfigSectionDescriptor(key=..., section=...)`

The object stores one String section key plus the R16 `ConfigSection` annotation and
implements the same `ConfigObject` name/description/position contract.

## Relationship to R16

R16 already recovered the surrounding configuration framework and referred to
ConfigItemDescriptor / ConfigSectionDescriptor structurally, but these three class identities
were not retained as semantic proposals. R389 closes those gaps.

R389 remains non-canonical semantic research only.
