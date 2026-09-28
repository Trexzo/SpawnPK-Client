# Chat 2 — exact-v308 chat-message classification R164

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R164 is a separate non-canonical class-only review for the central exact-v308 chat
message/channel classification utility.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_53C7F8CEB55D068C25EE`
- field/method proposals: **0**

## Stable ID

`rs/i/a` -> `CLIENT_CLASS_000296` -> `ChatMessageClassifier`

## Exact responsibility

The class has no instance state of interest. Its behavior is a static combination of:

- chat/message type constants;
- chat channel/filter constants;
- message reclassification;
- marker normalization;
- chat-line eligibility/filtering.

Its only project consumers are:

- `rs/Client`;
- `rs/i/b`.

The latter owns the exact gameframe chat-button surface containing:

- `All`;
- `Game`;
- `Public`;
- `Private`;
- `Clan`;
- `Trade`;
- `News`;
- `Yell`.

That renderer compares directly against the `rs/i/a` constants.

## Exact message reclassification

`a(String, int)` preserves the incoming type unless exact message content identifies a
special chat category.

The surviving rules include:

- exact News prefix
  `<img=2><shad=FFFF3F><col=FE610C> News: </shad></col>`;
- `<y>` -> Yell;
- the exact yell rate-limit form
  `Please wait at least ... each yell message!`;
- `<c>` -> Clan;
- `Clan Chat channel-mate` -> Clan.

## Marker normalization

`b(String, int)` removes only the exact channel markers associated with the corresponding
message type:

- `<c>`;
- `<y>`.

## Filtering / eligibility

`c(String, int)` applies exact-v308 chat-line filtering logic.

For ordinary system text it rejects generic/non-notification phrases such as:

- `you can`;
- `you must`;
- `you do`;
- `you need`;
- `is full`;
- `not enough`;
- `rules`;
- `costs`;
- `requires`;
- `players online`.

For News-style text the exact trigger vocabulary includes:

- `received`;
- `successfully enchanted`;
- `has killed`;
- `killstreak`;
- `has encountered`;
- `just captured`.

The Clan/Yell path additionally checks the exact icon list consumed by chat rendering.

## Naming boundary

`ChatMessageClassifier` is descriptive at **0.999**.

The name does not claim recovery of the original developer identifier. It follows the
whole-class behavior: all constants and methods are confined to chat message/channel typing,
classification, marker normalization and filtering.

R164 remains class-only.

## Exclusions retained

The unresolved `rs/n/c/aA` option-grid builder remains blocked: its roots 53500/53519 have
no second client-side owner/caller reference and its surviving text is still only generic
`Select option` / toggle wording.

The unused/dead-looking `rs/gui/e` sidebar utility panel is also not promoted merely from
its self-contained links/PK-command text because the current `ClientSidebarPanel`
constructor instantiates it but does not add it as a visible tab.

## Acceptance boundary

Chat 2 does not promote R164. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_53C7F8CEB55D068C25EE`.
