# Chat 2 — exact-v308 mail/coffer action prompts R113

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R113 is a separate non-canonical class-only review for the shared clickable action-prompt
overlay and its two exact-v308 concrete implementations.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_42DC3D073D4AAA33C51B`
- field/method proposals: **0**

## Stable IDs

- `rs/l/e/a/s` -> `CLIENT_CLASS_000417` -> `ActionPromptOverlay`
- `rs/l/e/a/r` -> `CLIENT_CLASS_000416` -> `MailNotificationOverlay`
- `rs/l/e/a/t` -> `CLIENT_CLASS_000418` -> `CofferClaimOverlay`

## ActionPromptOverlay

The abstract class extends R112 `InteractiveClientOverlay` and provides the complete
shared implementation for exactly two concrete subclasses.

Its LOW-layer renderer draws a 40x40 action prompt with:

- normal/hover sprite states;
- subclass-supplied colors;
- a shared sliding/alpha animation between 100 and 200;
- stacked placement using the R111 overlay counter;
- subclass-supplied hover/action text.

The interaction hook performs exact hit-testing over that prompt. A press inside the prompt
arms the action; a subsequent release invokes the subclass click action. While the prompt
owns the interaction it returns true, intercepting ordinary client menu construction
through R112.

## MailNotificationOverlay

The mail implementation loads:

- `misc/mail 7`;
- `misc/mail 8`.

Its click action writes:

`::mail`

to the client command field.

Its prompt text is exactly:

` <img=288> View`

This is sufficient to fix the role as the mail notification/action overlay.

## CofferClaimOverlay

The coffer implementation loads:

- `misc/treasure`;
- `misc/treasure 2`.

Its click action writes:

`::claimcoffer`

to the client command field.

Its prompt text is exactly:

` <img=9> Claim`

This fixes the role as the coffer-claim action overlay independently of the shared base.

## Naming boundary

No original source class nouns survive.

All three names are descriptive exact-behavior recovery. The shared base remains confidence
0.998; the concrete mail/coffer roles are confidence 0.999 because their resources,
commands and action text survive exactly.

## Acceptance boundary

Chat 2 does not promote R113. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_42DC3D073D4AAA33C51B`.
