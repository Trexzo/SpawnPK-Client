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

### `rs/n/c/ac` — `CLIENT_CLASS_000604`

Evidence:

- item search;
- tabs;
- item-list title/description placeholders;
- Deposit/Remove 1/5/10/All;
- deposit all to bank/inventory.

Blocker:

The class combines searchable-list and transfer semantics. Exact strings do not establish
whether this is a reusable item-list component, a bank/deposit surface, or a specific
higher-level content interface.

Required next evidence:

- exact interface root IDs and parent callers;
- dynamic item/container IDs;
- call sites that supply the title/content.

### `rs/n/c/d/a` — `CLIENT_CLASS_000651`

Evidence:

- `Public / Join`;
- `Select tab`;
- `raids/sprite 1..4`.

Blocker:

R3 already identifies distinct raid party list/hub/invitation/tome surfaces. This class is
clearly raid navigation, but current evidence is insufficient to distinguish a tab bar,
navigation shell, or reusable raid header.

Required next evidence:

- parent/child IDs and callers from R3 raid classes.

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

### `rs/n/c/ak` — `CLIENT_CLASS_000612`

Evidence:

- Home teleport;
- Edgeville teleport;
- Bounty teleport;
- Close Window.

Counter-evidence:

- class also loads `construction/sprite` and `LOGS/ICON`.

Blocker:

The literal role looks like a teleport shortcut menu but resource context suggests reuse or
a construction-adjacent surface. Do not choose a content name until ownership is proven.

### `rs/n/c/aA` — `CLIENT_CLASS_000576`

Evidence:

- generic `Select option`;
- `Selecting this option Toggle ...`.

Blocker:

No self-identifying content. Too generic for semantic promotion.

### `rs/n/c/f` — `CLIENT_CLASS_000659`

Evidence:

- player attack options;
- NPC/bot attack options;
- always right-click clan members;
- Select option.

Additional exact-v308 relationship evidence:

- R5 `ControlOptionsInterface` / `rs/n/c/ai` builds the main **35000** menu first;
- `rs/n/c/f` is registered later;
- `f` writes a subset of the same widget IDs used by `ai`, including
  **35091, 35096, 35102, 35107, 35112-35116**.

Current conclusion:

`f` is a later control-options attack/clan subsection or patch, not a second full
Control Options interface. It remains blocked because the exact responsibility boundary
(subsection builder vs post-build patch) is not yet proven strongly enough for a stable
semantic class name.

## Trust rule

Classes in this file remain **research leads only**. They should not be converted to
`semantic_name_candidate` rows by residual package order, neighboring names, or superficial
literal similarity.

Promotion requires evidence that distinguishes the class from already accepted/reviewed
surfaces, preferably interface IDs, call-site ownership, resource/root joins, or unique
behavioral flow.
