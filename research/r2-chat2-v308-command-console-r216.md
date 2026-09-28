# Chat 2 — exact-v308 command console R216

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R216 is a separate non-canonical class-only review for the exact in-game command-console
controller/renderer and its stored history-entry value.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_70C98BE24E8894C7D70C`
- field/method proposals: **0**

## Stable IDs

- `rs/l/e/b` -> `CLIENT_CLASS_000422` -> `CommandConsoleEntry`
- `rs/l/e/c` -> `CLIENT_CLASS_000423` -> `CommandConsole`

All stable IDs were recomputed from the exact v308 sorted `rs/**.class` seed-lineage order.

## CommandConsole

The identity is fixed by several independent exact-v308 paths.

### Direct activation and input ownership

The main Client input loop toggles `rs/l/e/c` directly on key code **96** (backtick).
When the console is active, normal typed input is diverted into this class.

The lower-level keyboard path independently routes:

- left/right arrows to the console cursor;
- up/down arrows to console history;
- typed characters into the current console input.

The class accepts printable input, handles backspace, preserves an editable cursor and
caps the current command at 80 characters.

### Exact command execution

On Enter, the class normalizes input around the exact `::` command prefix.

When the reviewed local command path is available it invokes R172
`ClientCommandProcessor`.

Otherwise it sends the command through the exact C2S103 command transport:

- packet id **103**;
- command-length byte;
- command text after the `::` prefix.

This is therefore a command console, not a generic text/chat editor.

### Dedicated rendered console

The render method owns a separate **320x100** translucent surface.

It draws:

- the exact `>` prompt;
- the editable command text;
- a blinking exact `|` cursor;
- stored console history beneath the prompt.

Both game render orchestrators invoke this renderer only while its active flag is set.

### History and output behavior

The console maintains:

- a bounded visible list;
- a larger command-history list;
- current history index;
- current input/cursor state.

It supports the exact `clear` command for visible history.

Submitted lines receive an exact `hh:mm a` timestamp. Rendered text also contains explicit
handling for `yell` and `news` prefixes plus legacy color-token formatting.

The key-remapping plugin independently checks whether this console is open and suppresses
its own shortcut handling while it is active.

## CommandConsoleEntry

`rs/l/e/b` is referenced only by `CommandConsole`.

Each instance stores:

- raw text;
- creation timestamp;
- optional preformatted display text.

Its sole accessor returns the display override when present and otherwise the raw text.

The console creates normal submitted-command entries with
`System.currentTimeMillis()` and the `hh:mm a` display prefix.

It also creates `~` sentinel entries whose display text is supplied directly, allowing
formatted console output to share the same history/render path.

That fixes this class as one command-console history/output entry rather than a generic
message model.

## Relationship to R164 and R172

R216 deliberately does not overlap:

- R164 `ChatMessageClassifier`, which classifies/filter-types normal chatbox messages;
- R172 `ClientCommandProcessor`, which executes recognized local client commands.

R216 owns the interactive console UI/history/input surface that feeds those command paths.

## Naming boundary

Both names are descriptive exact-behavior recovery at confidence **0.999**.

R216 does not claim original source identifiers and adds no field or method proposals.

## Acceptance boundary

Chat 2 does not promote R216. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_70C98BE24E8894C7D70C`.
