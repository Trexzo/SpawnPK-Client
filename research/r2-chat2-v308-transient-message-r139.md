# Chat 2 — exact-v308 transient message overlay / ScriptPacket 23 R139

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R139 resolves the previously withheld ScriptPacket 23 family with lifecycle-based names.
The exact binary does not identify the higher-level feature that supplies the text, so the
review deliberately avoids narrower nouns such as mail, achievement, tutorial or combat
notification.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_8AA6F31C46ED8B6EBF2A`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/a/a/a` -> `CLIENT_CLASS_000442` -> `TransientMessageEntry`
- `rs/l/f/a/a/c` -> `CLIENT_CLASS_000444` -> `TransientMessageOverlay`
- `rs/l/f/a/a/d` -> `CLIENT_CLASS_000445` -> `TransientMessagePacketHandler`
- `rs/l/f/a/a/e` -> `CLIENT_CLASS_000446` -> `TransientMessageAnimationState`

## Exact message record

Each entry owns:

- three Strings;
- one creation timestamp;
- current animation state;
- width/height/alpha presentation state.

The first String is rendered with `Client.gn`; the second and third use `Client.gl`.

The constructor timestamps the entry immediately and calculates its target width from all
three Strings, capped at **200** pixels.

## Exact animation state

The enum constants survive exactly:

- `EXPANDING_WIDTH`;
- `EXPANDING_HEIGHT`;
- `SHOWING`.

A new entry starts in `EXPANDING_WIDTH`.
After it reaches target width it enters `EXPANDING_HEIGHT`; after the height reaches its
60-pixel target it enters `SHOWING`.

The entry draws a temporary bordered/filled panel while these states advance.

## Queue overlay

`TransientMessageOverlay` extends the live overlay base and registers on overlay layer
`rs/l/f/a.v`.

It owns:

- one current message;
- a queued List of messages.

When no message is active, the overlay promotes one queued entry and resets that entry's
timestamp.

The current message is removed after exactly:

**5000 ms**

New entries are displayed immediately when no current entry exists. Otherwise they enter the
queue.

The queue policy is exact:

- compare all three Strings and reject an exact duplicate already queued;
- cap the queued list at **3** entries;
- when already at the cap, remove index 0 before appending the new entry.

## ScriptPacket 23

R115 registers `rs/l/f/a/a/d` directly as exact ScriptPacket **23**.

Its complete packet operation is:

1. read String 1;
2. read String 2;
3. read String 3;
4. obtain the live `rs/l/f/a/a/c` overlay from `rs/l/f/e`;
5. submit those three Strings.

There is no selector switch and no unrelated Client/gameplay mutation.

## Naming boundary

All four names are **0.999**.

`Message` is the narrowest safe content noun supported by the three rendered arbitrary
Strings. `Transient` is exact behavior from the five-second lifetime and animated
appearance/disappearance lifecycle.

R139 does not claim that the entries are a specific feature's notifications.

## Residual ScriptPacket boundary

After R139, the deliberately unnamed ScriptPacket frontier falls to four IDs:

- **8** — combat-stat-like overlay, higher-level feature noun still not proven;
- **27** — twelve-string HUD/overlay with no self-identifying domain;
- **32** — mixed handler with no honest single subsystem noun;
- **33** — 30700-series interface controller whose owning feature remains unidentified.

## Acceptance boundary

Chat 2 does not promote R139. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_8AA6F31C46ED8B6EBF2A`.
