# Chat 2 — exact-v308 Halloween Event Chest overlay / ScriptPacket 4 R130

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R130 resolves the previously ambiguous ScriptPacket 4 event-tier surface by proving its
exact widget/root relationship to the already-reviewed Halloween Event Chest interface.

R130 remains a separate non-canonical class-only review.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_B6AB56F35E65A6A41884`
- field/method proposals: **0**
- confidence: **0.998** each

## Stable IDs

- `rs/l/e/a/h` -> `CLIENT_CLASS_000406` -> `HalloweenEventChestOverlay`
- `rs/l/e/a/i` -> `CLIENT_CLASS_000407`
  -> `HalloweenEventChestOverlayPacketHandler`

## Exact root and widget authority

R3 already reviewed `rs/n/c/N` as `HalloweenEventChestInterface`.

That exact builder owns root **60600** and constructs the widget family used by the overlay,
including:

- **60611** — event-chest item slot;
- **60617**, **60618**, **60621** — tier-selection/presentation widgets;
- **60625** — tier progress/status text.

The same builder preserves:

- `Event Chest Tier I`;
- `Event Chest Tier II`;
- `Tier I - @yel@Halloween Event 2020`;
- `Roll`;
- `Exchange`;
- `@yel@Event Guide`;
- `fountain/event` resources.

## HalloweenEventChestOverlay

`rs/l/e/a/h` extends the client overlay base.

Its visibility predicate is exact:

`Client.cH == 60600`

so it renders only while the Halloween Event Chest interface root is live.

Its render path reads the same exact R3 widgets listed above.

The overlay itself preserves event-tier presentation including:

- `<img=81> You must roll all the items from the previous tier! <img=81>`;
- ` <img=81> Locked!`;
- `<img=46> @gre@You've completed this tier of the event! <img=46>`;
- `@gre@Congratulations! You've completed the entire event!`;
- `@yel@?`;
- `None`;
- `fountain/event 3`;
- `fountain/event 4`.

The central `rs/l/e/f` overlay bootstrap constructs and registers `rs/l/e/a/h` directly.

## ScriptPacket 4

R115 registers ScriptPacket **4** from `rs/l/e/a/h.D`.

Exact v308 initializes that field with:

`new rs/l/e/a/i()`

The complete selector surface is:

- **1**: clear the overlay completed-tier map and repopulate the first packet-specified
  tier indices as completed;
- **2**: update tier/progress values, derive progress text, write widget **60625**, and update
  the overlay's progress-bar state;
- **3**: update tier selection/state, swap exact sprites on **60617/60618/60621**, read the
  selected item from **60611**, and derive the overlay item text from its ItemDefinition;
- **4**: toggle the overlay's packet-controlled active state.

No selector mutates an unrelated subsystem.

## Naming boundary

`HalloweenEventChestOverlay` and its packet-handler name are descriptive, not original
source-identifier claims.

The noun is now supported by an exact chain:

R3 HalloweenEventChestInterface
-> root 60600
-> exact shared 606xx widgets
-> overlay visibility only on root 60600
-> exact event-tier completion/locked text
-> ScriptPacket 4 controlling only that overlay.

Confidence is **0.998** to preserve the distinction between exact behavioral identity and
lost original developer naming.

## Acceptance boundary

Chat 2 does not promote R130. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_B6AB56F35E65A6A41884`.
