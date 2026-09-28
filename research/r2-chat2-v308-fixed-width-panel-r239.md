# Chat 2 — exact-v308 RuneLite FixedWidthPanel source recovery R239

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_4A53B9777700E02BFC42`
- field/method proposals: **0**

## Stable ID

- `rs/s/b/h` -> `CLIENT_CLASS_000868` -> `FixedWidthPanel`

## Exact-v308 bytecode

The saved exact-v308 jar hashes to the pinned authority and shows:

- superclass: `javax.swing.JPanel`;
- no fields;
- constructor only;
- one override: `getPreferredSize()`.

That override returns:

`new Dimension(350, super.getPreferredSize().height)`

so the class is a constant-width panel wrapper with inherited/dynamic preferred height.

## Historical source provenance

RuneLite `68c819924cfd6bfb4848c71f74c121109f289d5a` contains
`net.runelite.client.plugins.config.FixedWidthPanel` with the same superclass and exact
single-method behavior:

`new Dimension(PluginPanel.PANEL_WIDTH, super.getPreferredSize().height)`

The RuneLite panel width in this source window is 350, matching v308 exactly.

Adjacent `rs/s/b/b..f`, `j/k`, `p`, `r`, and `s` are anonymous/listener/helper
classes or wrapper mechanics and remain unnamed unless a source identity is independently
proven.

## Acceptance boundary

Chat 2 does not promote R239. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_4A53B9777700E02BFC42`.
