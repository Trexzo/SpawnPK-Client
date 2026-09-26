# Chat 2 — exact-v308 configurable action prompt overlay R212

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R212 is a separate non-canonical class-only review for the callback-configurable 40x40
action-prompt overlay used by exact ScriptPacket 3, plus its two functional callback
interfaces.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_3E8CDB6083E99105DFC2`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/a/b/a` -> `CLIENT_CLASS_000447` -> `ConfigurableActionPromptOverlay`
- `rs/l/f/a/b/b` -> `CLIENT_CLASS_000448` -> `ActionPromptExecuteCallback`
- `rs/l/f/a/b/c` -> `CLIENT_CLASS_000449` -> `ActionPromptDrawCallback`

All IDs were recomputed from the exact v308 sorted `rs/**.class` seed-lineage order.

## Exact ScriptPacket 3 join

R118 already proves `rs/q/a/a/a/l` as
`MailCofferActionPromptPacketHandler` at ScriptPacket **3**.

That handler constructs exactly two `rs/l/f/a/b/a` instances:

- `<img=9> Claim`
  - `misc/treasure`
  - `misc/treasure 2`
  - action: `::claimcoffer`
- `<img=288> View`
  - `misc/mail 7`
  - `misc/mail 8`
  - action: `::mail`

The packet selector chooses one of those two prompt instances and the packet enable flag
adds/removes it through the live overlay manager.

This is therefore not a package-adjacency inference: the exact already-reviewed network
handler directly constructs and controls the reviewed class.

## ConfigurableActionPromptOverlay

The constructor receives:

- action/hover text;
- normal sprite name;
- hover sprite name;
- two colors.

It then fixes:

- size: **40x40**;
- exact render stage: `AFTER_WIDGETS_BEFORE_INTERFACE_HIGH`;
- exact placement: `TOP_RIGHT`.

The render path:

- lazily loads the two configured sprites;
- hit-tests the live mouse against the prompt rectangle;
- alternates opacity between 100 and 200;
- draws the configured background colors;
- switches between normal and hover sprites;
- displays the configured hover/action text;
- invokes the optional draw callback with `(x, y, opacity, hovered)`.

The activation hook schedules the optional execute callback.

The exact ScriptPacket-3 instances bind the two mail/coffer actions above, fixing the
class as a configurable action-prompt overlay rather than a generic decorative component.

## ActionPromptExecuteCallback

`rs/l/f/a/b/b` is a single-method functional interface:

`void execute()`

Its only concrete consumer is `ConfigurableActionPromptOverlay`.

ScriptPacket 3 supplies two lambdas whose exact bodies send:

- `::claimcoffer`;
- `::mail`.

The callback therefore owns prompt activation behavior.

## ActionPromptDrawCallback

`rs/l/f/a/b/c` is a single-method functional interface:

`void draw(int, int, int, boolean)`

Its only concrete consumer is `ConfigurableActionPromptOverlay`, which passes:

- prompt x;
- prompt y;
- current opacity;
- hover state.

ScriptPacket 3 supplies this callback for both prompt instances; both callback bodies draw
the same client sprite at a prompt-relative offset.

This fixes it as the prompt render-extension callback.

## Relationship to R113

R113 already owns the separate older/parallel family:

- `ActionPromptOverlay`;
- `MailNotificationOverlay`;
- `CofferClaimOverlay`.

R212 does **not** duplicate those names or owners.

The exact-v308 bytecode proves a second implementation path: ScriptPacket 3 builds the
mail/coffer prompts by configuring one reusable overlay class with callback lambdas instead
of instantiating the R113 concrete subclasses.

The qualifier `Configurable` is therefore deliberate and evidence-backed.

## Naming boundary

All three names are descriptive exact-behavior recovery at confidence **0.999**.

R212 does not claim original source identifiers and adds no field or method proposals.

## Acceptance boundary

Chat 2 does not promote R212. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_3E8CDB6083E99105DFC2`.
