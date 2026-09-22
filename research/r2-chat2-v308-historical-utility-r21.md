# Chat 2 — exact-v308 historical utility semantics R21

Exact SpawnPK client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R21 is a deliberately small non-canonical class-only semantic review batch. It does not
alter Main/Core's accepted R2 semantic authority or prior R3-R20 review batches.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_A9CC34F7D0E7034AAAE4`
- field/method proposals: **0**

## Jagex printable character matcher

- `rs/A/k` -> `JagexPrintableCharMatcher`

Exact SpawnPK v308 evidence:

- the class extends Guava `CharMatcher`;
- its match predicate accepts ASCII codepoints 32..126, codepoint 128, and 160..255;
- the exact-v308 `Text` utility instantiates this class as its Jagex printable-character
  matcher used during text/message sanitization.

Historical-origin cross-check only:

RuneLite commit
`a5c2494fc913d5b6023edc7883c4933c948f852e` contains
`net.runelite.client.util.JagexPrintableCharMatcher` with the identical matcher predicate.

The SpawnPK v308 structure remains the semantic authority; the historical name is supporting
provenance rather than a substitute source.

## macOS fullscreen adapter

- `rs/A/n` -> `OSXFullScreenAdapter`

Exact SpawnPK v308 evidence:

- extends `com.apple.eawt.FullScreenAdapter`;
- stores one `Frame`;
- fullscreen entry sets `Frame.MAXIMIZED_BOTH`;
- fullscreen exit sets `Frame.NORMAL`;
- installs through `FullScreenUtilities`;
- exact diagnostics are:
  - `Window entered fullscreen mode--setting extended state to {}`
  - `Window exited fullscreen mode--setting extended state to {}`

Historical-origin cross-check only:

The same RuneLite historical commit contains
`net.runelite.client.ui.OSXFullScreenAdapter` with the same superclass, Frame state
transitions, diagnostic strings and install helper.

## Deliberate exclusions

R21 does **not** force identities for the other remaining nearby `rs/A` internals:

- custom AssetIcon cache loaders;
- the SpawnPK Gson Color serializer/deserializer;
- the macOS focus/user-attention helper.

Those classes have useful role evidence, but their exact historical source identity is not
yet established strongly enough for this batch.

## Acceptance boundary

Chat 2 does not promote R21. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to
`SEMREVIEW_A9CC34F7D0E7034AAAE4`.
