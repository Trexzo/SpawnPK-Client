# Chat 2 — exact-v308 sent private-message ScriptPacket R120

Exact client authority: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R120 is a separate non-canonical class-only review for the direct ScriptPacket handler whose exact chat type is the outgoing private-message channel.

## Result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_077E34656C4BB246BE21`
- field/method proposals: **0**

## `rs/q/a/a/a/o` -> `SentPrivateMessagePacketHandler`

Stable ID: `CLIENT_CLASS_000760`.

R115 registers the class as ScriptPacket **38**.

For selector 1 it reads:

- one long username value;
- one message String.

The long is decoded and normalized through `rs/O`, after which the handler calls:

`Client.a(message, 6, username)`

Exact v308 initializes `rs/i/a.o` to **6**. The chat renderer's corresponding branch uses the surviving literals:

- `To <name>:`
- `To <name>`

and applies private-chat visibility behavior.

Incoming private chat uses the separate type-7 path that posts `PrivateChatMessage`, so type 6 is specifically the sent/outgoing private-message channel.

That fixes the handler identity independently of the obfuscated class name.

## Boundary

R120 remains class-only and does not rename the global chat-type constants or Client chat arrays.

## Acceptance

Chat 2 does not promote R120. Main/Core may accept the proposal only through an explicit `semantic_acceptance_spec` bound to `SEMREVIEW_077E34656C4BB246BE21`.
