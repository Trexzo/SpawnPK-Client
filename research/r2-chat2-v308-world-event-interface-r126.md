# Chat 2 — exact-v308 Gladiator's Vindication World Event ScriptPacket 10 R126

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R126 is a separate non-canonical class-only review for the direct ScriptPacket handler
whose complete selector surface controls the recovered Gladiator's Vindication World Event
interface.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_18F45D97BD3C38C9A5C7`
- field/method proposals: **0**

## Stable ID

`rs/n/c/b/d` -> `CLIENT_CLASS_000638`
-> `GladiatorsVindicationWorldEventInterfacePacketHandler`

R115 registers this class directly as ScriptPacket **10**.

## Existing target authority

R3 recovered `rs/n/c/b/a` as:

`GladiatorsVindicationWorldEventInterface`

from exact v308 presentation evidence including:

- `Gladiator's Vindication (World Event)`;
- `Event duration ends in: @yel@<img=37> 14 days`;
- progress-bar vocabulary;
- selectable button/option vocabulary;
- `event/task`, `event/task 1`, `event/task 2`, `event/task 3`;
- supporting drops/fountain resources.

ScriptPacket 10 mutates that exact subsystem.

## Complete selector surface

The handler implements selectors **0–10**.

The branches remain coherent around one World Event interface responsibility:

- **0** resets the dynamic event-option/task list and current event selection state;
- **1** appends a packet-provided task/option String;
- **2** updates the event progress graphic from a packet percentage value;
- **3** toggles an event widget;
- **4** toggles the event root/interface state and resets the client-side selected widget;
- **5** updates one indexed event task/option String;
- **6** selects the current event key and synchronizes the two event scroll/list positions;
- **7** reflows the dynamic option widgets, clears unused rows and recalculates scroll height;
- **8** writes a packet-provided scroll/list position to the same event widgets;
- **9** resets those positions and removes the current event key from the local event map;
- **10** updates the selected event option's dynamic text.

Selector 2 specifically rewrites widget **57222** with the exact
`event/task 2` resource after scaling the packet percentage across the 367-pixel progress
surface.

The handler's widget writes remain in the same **56997–57223** interface range and the same
`rs/n/c/b` state used by the recovered World Event interface.

## Naming boundary

`GladiatorsVindicationWorldEventInterfacePacketHandler` is descriptive at **0.998**.

The event title itself survives exactly, the target interface already has a reviewed semantic
identity, R115 fixes ScriptPacket 10, and all eleven selectors remain inside that interface's
task/progress/selection/layout state.

The English handler name is not claimed as a surviving original class identifier.

R126 remains class-only.

## Deliberate exclusions

ScriptPacket 32 remains unnamed.

The other currently unreviewed direct handlers are not pulled into R126 merely to increase
proposal count; weaker overlay families remain research-only until their nouns are independently
fixed.

## Acceptance boundary

Chat 2 does not promote R126. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_18F45D97BD3C38C9A5C7`.
