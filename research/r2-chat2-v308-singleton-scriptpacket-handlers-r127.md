# Chat 2 — exact-v308 singleton-backed ScriptPacket interface handlers R127

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R127 is a separate non-canonical class-only review for six ScriptPacket handlers whose
registrations are indirect through subsystem-owned singleton fields. The concrete classes
were resolved from the exact v308 static initializers rather than inferred from field names.

## Deterministic review result

- candidate classes: **6**
- resolved proposals: **6**
- unresolved: **0**
- review ID: `SEMREVIEW_EC7BF9DFB04042D59C6D`
- field/method proposals: **0**

## Exact registration resolution

| ScriptPacket | Dispatcher singleton field | Exact concrete class | Stable ID | Proposal |
| ---: | --- | --- | --- | --- |
| 6 | `rs/n/c/J.c` | `rs/n/c/K` | `CLIENT_CLASS_000557` | `EventActivityViewerInterfacePacketHandler` |
| 9 | `rs/n/c/ag.e` | `rs/n/c/ah` | `CLIENT_CLASS_000609` | `ItemsKeptOnDeathInterfacePacketHandler` |
| 13 | `rs/n/c/O.c` | `rs/n/c/P` | `CLIENT_CLASS_000562` | `ActiveEventsInterfacePacketHandler` |
| 15 | `rs/n/c/V.bI` | `rs/n/c/W` | `CLIENT_CLASS_000569` | `GamblingInterfacePacketHandler` |
| 30 | `rs/s/t/i.b` | `rs/s/t/j` | `CLIENT_CLASS_000972` | `TradingPostPacketHandler` |
| 35 | `rs/n/c/aq.f` | `rs/n/c/ar` | `CLIENT_CLASS_000622` | `MakeQuantityInterfacePacketHandler` |

The dispatcher calls `getClass()` on each singleton field. Each owning class's exact static
initializer constructs the concrete class listed above and stores it into that field.

## ScriptPacket 6 — Event Activity Viewer

`rs/n/c/J` preserves the exact title:

`Event Activity Viewer`

along with token-limit, activity-lock and timer-reset text plus
`popups/activities 1` / `popups/activities 2`.

The concrete handler `rs/n/c/K` has three selector modes:

- 0 clears the activity record list and resets viewer state;
- 1 reads one activity name, a packet-sized String array, two integers and one long, then
  delegates the complete record into `rs/n/c/J`;
- 2 invokes the viewer finalization/refresh path.

There is no non-viewer branch.

## ScriptPacket 9 — Items kept on death

`rs/n/c/ag` preserves:

- `Items kept on death`;
- `Items I will keep...`;
- `Items I will lose...`;
- `Items I will auto-keep...`;
- red-skull/prayer loss explanatory text;
- `icons/death` and equipment resources.

The concrete handler `rs/n/c/ah` only:

- clears the interface-owned integer Set; or
- reads one integer and adds it to that Set.

That is the complete class.

## ScriptPacket 13 — Active Events

`rs/n/c/O` preserves active-event presentation including:

- `<img=100> View Active Events`;
- `<img=100> View all events`;
- `Event Global Boss`;
- `Event Wildy Boss`;
- event countdown/status strings;
- hotspot/vote state.

The concrete handler `rs/n/c/P` selectors 1–7 write only `rs/n/c/O` state.
Packet longs become absolute client deadlines by adding `System.currentTimeMillis()`;
paired Strings and integers update the same event display/status surface.

## ScriptPacket 15 — Gambling interface state

`rs/n/c/V` is self-identifying from:

- `gambling/SPRITE`;
- `Gambling with P1..`;
- 55x2 and blackjack host modes;
- Dice duel;
- Flower poker;
- offer accept/decline;
- gambling safety/rules text.

The concrete handler `rs/n/c/W` has only one implemented selector. It writes one
packet-controlled boolean-like value and one current-time timestamp into `rs/n/c/V`.

R127 deliberately does **not** assign semantic names to those two fields. The class-level
handler identity is supported even though the narrower field meanings remain unknown.

## ScriptPacket 30 — Trading Post

`rs/s/t/i` preserves exact `Trading Post` identity and owns the already-reviewed Trading
Post panel graph.

The concrete handler `rs/s/t/j` implements two operations:

1. build one `rs/s/t/c` listing model from four packet integers, a packet-selected
   `rs/s/t/b` currency enum and the exact ItemDefinition name, then add it through the
   Trading Post panel/listings container;
2. read one integer and remove the corresponding listing through that same container.

No other domain is touched.

## ScriptPacket 35 — Make Quantity

`rs/n/c/aq` preserves:

- `How many would you like to make?`;
- `Choose a quantity, then click an image to begin.`;
- `Select quantity`;
- 1 / 5 / 10 / X / All controls;
- `options/make/sprite` resources.

The concrete handler `rs/n/c/ar` implements selectors 0–4 entirely within the same
55301–55330 widget group and `rs/n/c/aq` helpers:

- option/item icon and quantity data;
- quantity button selection/reset state;
- title/subtitle and layout visibility;
- formatted per-option text;
- option timing/selection state.

## Naming boundary

These are handler-role names, not claims that original source identifiers survived.

Confidence is **0.999** for the five handlers whose target domain and packet operations are
both explicit. `GamblingInterfacePacketHandler` is **0.998** because its two target fields
remain semantically unnamed even though the containing interface is exact and exclusive.

R127 remains class-only.

## Deliberate exclusions

R127 does not absorb weaker singleton/direct handlers merely to increase count.

In particular:

- ScriptPacket 32 remains unnamed because its full selector surface is mixed;
- ScriptPacket 36 remains research-only because the handler writes `rs/n/c/ay` state and
  the exact authority bridge from that state object to the Donation Shopping Cart interface
  has not yet been documented strongly enough;
- the weaker direct overlay handlers remain unproposed until their overlay nouns are fixed
  independently.

## Acceptance boundary

Chat 2 does not promote R127. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_EC7BF9DFB04042D59C6D`.
