# v309 R281 — real GUI Cave Entrance Enter and follow-up walking

**2026-10-18. Sole-client-owner continuation of R280.** Existing #1142 remains **DRAFT**, no merge to main. **No production source changes.** The actual compiled binary is the independently built and hashed R278 Java11-target 1,386-class v309 client with its R274/R278 scene-authority guards, SHA256 \`dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd\`.

## Main end-to-end result: two independent GUI/localhost replays

The mock server sent source-framed opcode60 containing **four original cached object IDs** in a nonoverlapping, experimentally positioned scene:

- ID2 **Cave Entrance**, model731, 4×2 footprint at local (49,50)
- ID114 **Cooking range**, model5274, rotated orientation1 to 2×1 at local (50,49)
- ID104 **Open chest**, model1226 at local (52,49)
- ID152 **Compost heap**, model1428 at local (53,52)

The genuine source-built GUI (1400×900 Linux/Xvfb with user's unmodified private cache and only original-JAR **nonclass** resources) displayed **Enter Cave Entrance** on an authentic AWT right-click at screen (480,285) **after allowing the pending model to become pickable**. AWT left-click at (420,314) selected the real first option. The original client emitted **opcode132/6** for **object ID2**, world tile **(3201,3202)**, independently received/ISAAC-decoded by the 127.0.0.1:43594 mock listener at raw offset **52**. It returned explicit synthetic **opcode253** chat text, *Object 2: isolated test interaction.*

The same client then received a second AWT left-click on open ground at (310,315); real client pathfinder emitted **opcode164/8** at received offset **60**. The listener returned source-framed opcode81/68 placing the actor at local tile **(46,51)**. Both actual screen snapshots remained populated and original client PacketCapture independently verified outgoing **121**, **132**, **164**, incoming **253**, and **81/68**.

- Replay 1 in a separately staged disposable test home: received **59-byte** action ciphertext and **69-byte** complete outbound wire, latter SHA256 \`42c0a059aaf16cd61769acae1e872e05d6a6301a77518599b862e68b626a6a45\`; viewport after walking **99.83%** nonblack.
- Replay 2 from a **brand-new owner-input-hash-guarded test home**, populated with all **10,772 authentic cached files**: independently reproduced the same action and walk offsets, world/local coordinates, and renderer acceptance; final 69-byte wire SHA256 **\`92a27740e82f4bc4a2bbfd9977215187c114fd169a7f97d6b65ae8772d7634bf\`** (independent ephemeral ISAAC state); final viewport **99.82%** nonblack. The fresh script explicitly checked the child GUI runner exit code 0.

**Readiness finding:** a preceding attempt clicked too soon after the global scene-rendered flag became true; the right-click menu then only offered Walk here, and the client emitted walking frames instead of opcode132. The reproduced success uses a **6-second test-harness delay** after first graphical rendering. This is an object model/scene-promotion acceptance condition in the synthetic fixture, not a proven production rendering defect or a production client patch.

## Cooking range investigation — source-backed identity ambiguity, GUI Cook still not accepted

An independently compiled **actual R278 class + authentic config** Java regression passed **28/28 checks** and found multiple cached object definitions with the same rendered name:

| Definition ID | Name | Model | Footprint | First option |
|---:|---|---:|---|---|
| 114 | Cooking range | 5274 | 1×2 | **Cook** |
| 16641 | Cooking range | 5274 | 1×2 | **Cook** |
| 4172 | Cooking range | 1219 | 1×2 | **none** |
| 22154 | Cooking range | 22943 | 2×1 | **none** |
| 2 | Cave Entrance | 731 | 4×2 | **Enter** |

Actual graphical menu-position sweeps with the rotated cooking range moved to two locations repeatedly showed **Examine Cooking range** but not **Cook**. A same-name no-action scene object is a plausible reason, **but the exact live Model.field229 picked ID has not been captured**. Do not assert the GUI action is fixed, do not ascribe the observed Examine menu to ID4172 without a real model-pick ID witness. Next inspect the actual click-selection field/scene hash and verify GUI Cook before treating it as usable.

## Verification package and provenance boundary

One reproducibly generated **public-safe R281 evidence ZIP** \`SpawnPK_v309_R281_CAVE_ENTER_WALK_GUI_EVIDENCE.zip\`, SHA256 **\`97d14140321bfa436a23420660f1353b6e99127ff68093958b4fbb8c6428d179\`**, **1,934,614 bytes, 40 entries**. Two independent deterministic builds are byte-identical; all CRC/manifest SHA checks PASS. Actual offline Java cache identity regression **28/28 PASS**; independent Pillow-based evidence verifier **195/195 PASS**, covering both actual 59/69-byte received streams, source packet captures, action/reply pairing, real AWT click logs, source-backend movement acknowledgment and screenshot rendering.

Archive provides synthetic mock server/ISAAC decoder, source-safe cache staging, SHA-pinned **fresh homeowner replay runner**, Robot sources, screenshot/evidence captures from both independent GUI runs, original object identity Java test, independent Python evidence validator. No private game source, compiled client JAR, dependencies, actual cache contents, non-class original resources or genuine credentials redistributed.

Original owner input SHA256s:
- R278 private build ZIP: \`e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280\`
- R265 private ZIP: \`9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb\`
- Original \`.spawnpk (4).zip\`: \`8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565\`
- Original client JAR used for non-class resources **only**: \`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38\`
- Original resource-map capsule: \`5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125\`

**Remaining:** true cave/dungeon transition and genuine gameplay world server semantics, Cooking range Cook GUI, native Windows graphical runtime, original server authentication, long-term stable game sessions, original binary bytecode parity and physical power loss unverified. No production code changed, no real user install. Keep #1142 DRAFT, no main merge.

**Next R282:** capture actual scene-picked object ID/model hash for Cooking range variants and resolve why graphical Cook is absent; expand GUI collision/path acceptance with a precise readiness gate; then native Windows owner acceptance at a meaningful milestone.

## R282 follow-up correction — definition bank is part of the evidence

The earlier R281 28-check object-identity test called `ObjectDefinition.load(new Archive(...))`, which on these inputs leaves **OSRS-config bank `field1136`** active; therefore ID114's **Cook** option in that test is valid for the OSRS configuration only. R282 instrumented the **actual GUI scene picker**, finding exact ID114 at local (51,49) in region12593's **standard bank `field1133`**, with both normal and raw action decodes **null**, no cached override or transform. The standard region's Examine-only menu is correct. New explicit three-bank + reset regression 78/78 and independently rerun R278 797/797 pass. See `docs/V309_R282_COOKING_RANGE_DEFINITION_BANK_GUI_ROOT_CAUSE.md`. Do not introduce a global Cook patch or infer a scene-picked duplicate ID from R281's OSRS-mode test.
