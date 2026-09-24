# Chat 2 — exact-v308 UI ambiguity triage

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

This file records high-signal exact-v308 UI classes that Chat 2 deliberately **did not**
promote into semantic candidates after R3-R6.

The goal is to preserve the evidence and the blocker instead of forcing a plausible English
name.

## Blocked classes

### `rs/n/c/C` — `CLIENT_CLASS_000548` — RESOLVED

Initial evidence showed a second donation-cart implementation, but the first pass deliberately
withheld a `Legacy*` label.

The missing proof is now present from exact-v308 bytecode:

- `C.a()` builds root interface **60200** and the exact title
  `Donation Shopping Cart Interface`;
- accepted `rs/n/c/aw.a()` later builds the **same root 60200**;
- `rs/n/d` registration executes each builder immediately through `rs/n/c.a()`;
- registration order calls `C` first and `aw` later, so `aw` supersedes the same root
  widget tree during startup;
- `aw` additionally exposes the action-handler registration consumed from
  `rs/q/a/a/b`, while `C` has no equivalent external handler registration.

This is sufficient to move the class out of ambiguity triage into R7 as:

`LegacyDonationShoppingCartInterface`

Review ID: `SEMREVIEW_9D3D080DCFC1237F346E`.

### `rs/n/c/ac` — `CLIENT_CLASS_000604` — RESOLVED

R122 later supplied the missing root/runtime evidence:

- exact root **36000**;
- item-list title/description placeholders;
- five tab controls;
- search input/results;
- Remove/Deposit 1/5/10/All;
- deposit-all bank/inventory actions;
- ScriptPacket 14 exclusively controls the same 36000-series list/search state.

Moved to R122 as:

`ItemListInterface`

Review ID: `SEMREVIEW_761085F0BAEBCC13F99B`.

### `rs/n/c/d/a` — `CLIENT_CLASS_000651` — RESOLVED

The previously missing parent/root evidence is now exact:

- the class appends one shared raid shell to roots **32300, 32297, 32299, 32298 and 32600**;
- that shell owns `Party`, `Public / Join`, `Invocations` and `Select tab`;
- exact resources include `raids/tabactive`, `raids/tabinactive` and
  `raids/tabdisabled`;
- the composed roots are populated by the separately recovered
  `RaidPartyHubInterface`, `RaidPartyListInterface` and `AfflictionTomesInterface`;
- R123 ScriptPacket 41 updates the same class's live navigation/tab state.

This distinguishes a reusable raid navigation shell from a page-specific content builder.

Moved to R135 as:

`RaidNavigationInterface`

Review ID: `SEMREVIEW_2C4368F6B1F9C2755E43`.

### `rs/n/c/Y` — `CLIENT_CLASS_000571` — RESOLVED

Exact bytecode now proves this is the gameframe navigation strip:

- root **32000**;
- Achievements -> **44100**;
- Account Information -> **638**;
- Knowledgebase -> **64600**;
- World Events -> **40087**;
- PK Ratings -> **40403**.

Moved to R8 as `GameframeNavigationInterface`.

### `rs/n/c/aa` — `CLIENT_CLASS_000602` — RESOLVED

The missing parent/root evidence is now exact:

- `GameframeNavigationInterface` routes **Account Information** to root **638**;
- `aa.a()` directly obtains and populates **638**;
- Achievement Diary, Monster drop tables and Hotspot are content inside that root.

Moved to R8 as `AccountInformationInterface`.

### `rs/n/c/ak` — `CLIENT_CLASS_000612` — RESOLVED

Exact root ownership resolves the earlier resource ambiguity:

- the class builds root **48999**;
- its only content actions are Home teleport, Edgeville teleport and Bounty teleport;
- the only other action is Close Window;
- there is no construction state or construction behavior in the class;
- exact dependency analysis finds no project caller beyond the interface registry.

The `construction/sprite` and `LOGS/ICON` paths are therefore presentation reuse, not the
semantic owner.

Moved to R137 as:

`TeleportShortcutInterface`

Review ID: `SEMREVIEW_C6CFB2BCCB39A2EFAC37`.

### `rs/n/c/aA` — `CLIENT_CLASS_000576`

Evidence:

- generic `Select option`;
- `Selecting this option Toggle ...`.

Blocker:

No self-identifying content. Too generic for semantic promotion.

### `rs/n/c/f` — `CLIENT_CLASS_000659` — RESOLVED

The responsibility boundary is now exact:

- `rs/n/c/f` builds child root **35112** with 13 children;
- its own text is Player attack options, NPC/Bot attack options and
  Always right-click clan members;
- the R5 `ControlOptionsInterface` owns parent root **35000**;
- root 35112 embeds the parent-created attack dropdown widgets
  **35091/35096/35102/35107**;
- parent runtime layout code also moves/hides those same widgets inside root 35112;
- exact registration builds `rs/n/c/ai` first and `rs/n/c/f` later.

This proves a dedicated attack/clan settings child interface rather than a second full
Control Options menu or an unrelated patch.

Moved to R136 as:

`ControlOptionsAttackSettingsInterface`

Review ID: `SEMREVIEW_E9153D754ABB6B3C9812`.

## Trust rule

Classes in this file remain **research leads only**. They should not be converted to
`semantic_name_candidate` rows by residual package order, neighboring names, or superficial
literal similarity.

Promotion requires evidence that distinguishes the class from already accepted/reviewed
surfaces, preferably interface IDs, call-site ownership, resource/root joins, or unique
behavioral flow.
