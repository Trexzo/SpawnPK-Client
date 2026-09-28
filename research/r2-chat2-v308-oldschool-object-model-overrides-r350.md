# Chat 2 — exact-v308 old-school object model overrides R350

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/c/a/a` -> `CLIENT_CLASS_000080` -> `OldSchoolObjectModelOverrides`
- proposal: `SEMPROP_AA02B66A159291F2A957`
- review: `SEMREVIEW_CDE25DFEBEFB618396DD`

## Exact caller gate

R28 already fixes `rs/d/r` as `ObjectDefinition`.

During definition load, ObjectDefinition checks its definition-mode enum. The override call is
made only when that mode equals the preserved enum constant:

`OLDSCHOOL`

The other preserved modes are `STANDARD`, `NEW` and `OSRS`.

## Exact mutation surface

The utility has two static methods taking:

- `ObjectDefinition`
- object id

The large method contains an approximately 680-id lookup switch. Every case writes the same
field:

`ObjectDefinition.an : int[]`

That field is the definition's model-id array.

The public wrapper first invokes the large table and then applies a second eight-id correction
switch, again writing only the same model-id array.

Representative replacement model IDs include custom 50xxx values alongside ordinary object
model IDs.

## Boundary

This is **not** a general ObjectDefinition override utility.

Exact bytecode shows no writes to:

- name/actions;
- dimensions/collision;
- animation;
- recolor/retexture;
- interaction flags;
- morph state.

The recovered responsibility is specifically OLDSCHOOL-mode object model-ID remapping.

R350 remains non-canonical semantic research only.
