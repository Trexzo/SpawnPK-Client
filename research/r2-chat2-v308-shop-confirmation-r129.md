# Chat 2 — exact-v308 shop-tab and confirmation ScriptPacket handlers R129

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R129 is a separate non-canonical class-only review for two remaining exact ScriptPacket
surfaces with complete, single-domain handler responsibilities.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_A499433BF6E1D5E1F0FB`
- field/method proposals: **0**
- confidence: **0.998** each

## Stable IDs

- `rs/n/c/aP` -> `CLIENT_CLASS_000591`
  -> `ShopTabInterfacePacketHandler`
- `rs/n/c/A` -> `CLIENT_CLASS_000545`
  -> `ConfirmationInterface`
- `rs/n/c/B` -> `CLIENT_CLASS_000547`
  -> `ConfirmationInterfacePacketHandler`

## ScriptPacket 17 — ShopTabInterfacePacketHandler

R115 registers ScriptPacket **17** from `rs/n/c/aO.g`.

Exact v308 initializes that field with:

`new rs/n/c/aP()`

R6 already reviewed `rs/n/c/aO` as `ShopTabInterface`. Its exact presentation preserves:

- `Main stock`;
- `Right-click on shop`;
- `Select shop tab`;
- `Tab 1` through `Tab 5`;
- the 41043–41052 shop-tab widget group.

The complete `rs/n/c/aP` selector surface is:

- **0**: reset tab 0 through `rs/n/c/aO.a(0, rs/n/c/aO.c)`;
- **1**: read tab index, String count and that many packet Strings, then call
  `rs/n/c/aO.a(index, strings)`;
- **2**: read one integer and call `rs/n/c/aO.m(value)`.

There is no cross-domain branch.

## ConfirmationInterface

`rs/n/c/A` builds and manages one dedicated confirmation prompt widget family.

Exact surviving presentation includes:

- `Confirm`;
- `Cancel`;
- `<img=25> Close window`;
- `Please confirm your choice.`.

The class configures the 14170-series widgets, including optional image/content positions
and the confirm/cancel presentation. Its interface-builder entry point initializes that
surface and changes widget 14175 to exact text `Confirm`.

No prior R3-R128 semantic review owns `rs/n/c/A`.

## ScriptPacket 28 — ConfirmationInterfacePacketHandler

R115 registers ScriptPacket **28** from `rs/n/c/A.c`.

Exact v308 initializes:

`new rs/n/c/B()`

into that field.

The complete handler surface is:

- **0**: read one boolean-like integer and call `rs/n/c/A.a(boolean)`;
- **1**: call `rs/n/c/A.h()`;
- **2**: read two integers plus a boolean-like value and configure confirmation widget
  **14171** through `rs/n/c/A.a(14171, x, y, 167, 123, flag)`;
- **3**: read two integers plus a boolean-like value and configure widget **14172** through
  `rs/n/c/A.a(14172, x, y, 32, 32, flag)`, then set that same widget's `aT` to 1000.

No selector touches unrelated Client state.

## Naming boundary

These are descriptive readable names, not claims that original source identifiers survived.

`ConfirmationInterface` is grounded directly in exact confirmation text and a dedicated
widget tree, while its handler and ShopTab handler are fixed by exact ScriptPacket
registration plus complete single-domain selector surfaces.

All three remain at **0.998** to preserve the distinction between exact behavioral/domain
identity and lost original developer identifiers.

## Deliberate exclusions

ScriptPacket 32 remains unnamed.

The remaining weaker overlay/event handlers are not included merely to increase proposal
count; they remain research-only until their complete target nouns are independently fixed.

## Acceptance boundary

Chat 2 does not promote R129. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_A499433BF6E1D5E1F0FB`.
