# Chat 2 — loadout codec/version + GUI image asset R345

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/b/b/c` -> `CLIENT_CLASS_000239` -> `LoadoutBinaryCodec`
- `rs/gui/b/b/e` -> `CLIENT_CLASS_000241` -> `LoadoutFormatVersionDetector`
- `rs/gui/x` -> `CLIENT_CLASS_000285` -> `GuiImageAsset`
- review: `SEMREVIEW_3F189A9A805A7FF3CCB3`

## Loadout binary codec

R143 already fixes the surrounding model/persistence graph:
`LoadoutDefinition`, `LoadoutFolder`, `LoadoutManager`, `LoadoutPersistence`,
`LoadoutEquipmentSlot`, and `LoadoutSpellbook`; R144 adds `LoadoutIcon` and
`LoadoutItemEntry`.

`rs/gui/b/b/c` is the exact model codec underneath that persistence layer.

Its writer serializes the full LoadoutDefinition graph to DataOutputStream. Its reader
reconstructs LoadoutDefinition instances from DataInputStream and inserts them into the
target LoadoutFolder.

## Loadout format version detector

`rs/gui/b/b/e` scans the exact LoadoutPersistence directory for files prefixed with the
supplied key plus `_ver_`, parses the suffix and retains the highest discovered version.

It starts at version 1, exposes current format constant 5, and the codec uses
`a(version)` gates for versions 2/3/4/5 to decode fields introduced across revisions.

## GUI image asset

`rs/gui/x` is a shared GUI resource image holder/draw helper.

It:

- loads filesystem assets when Client.class is running from a file URL;
- otherwise loads the same resources from the classpath;
- stores mutable x/y draw coordinates;
- renders the held Image through Graphics2D.

Consumers span equipment slots, loadout icons/categories, skill/prayer artwork and other
sidebar assets, so the role is deliberately generic.

## Withheld

`rs/gui/b/b/a` has no exact external references and remains unnamed.

R345 remains non-canonical semantic research only.
