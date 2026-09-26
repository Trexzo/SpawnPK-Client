# Chat 2 — exact-v308 client command processor R172

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R172 is a separate non-canonical class-only review for the central client-side command
parser/dispatcher and command-forwarding queue.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_0AC5B516E2D050415E42`
- field/method proposals: **0**

## Stable ID

`rs/n/a` -> `CLIENT_CLASS_000525` -> `ClientCommandProcessor`

The stable ID follows the canonical exact-v308 R1 `rs/` baseline ordering.

## Command entry point

The public entry point receives:

- the live `Client`;
- a command String;
- one privilege/context integer.

It rejects an empty String, strips the exact:

`::`

prefix, splits the remaining text into the command key plus String arguments and dispatches
the command locally.

It always invokes the common local command table. When the exact privilege/context predicate
`rs/l/j.b(int)` passes, it also invokes the larger privileged/debug command table.

This makes the class a command processor rather than one specific command implementation.

## Common local command table

The smaller local table preserves exact command keys including:

- `cmdmode`;
- `chatcmd`;
- `chatcmdmode`;
- `hween`;
- `snow`;
- `winter`;
- `xmas`;
- `summer`;
- `darkwinter`;
- `darkxmas`;
- `renderself`;
- `multi`.

The handlers directly toggle client configuration/theme/render state and emit exact
enabled/disabled feedback such as:

- `<img=2> Chat command mode has been:`;
- `Type chatcmd to toggle it back off!`;
- character-render enabled/hidden messages;
- wilderness minimap multi-line visibility feedback.

## Privileged/debug command table

The larger exact table contains **32** command keys.

Surviving examples include:

- `checkscreen`;
- `repack`;
- `gfxdata`;
- `animdata`;
- `macaddress`;
- `dumpclip`;
- `tipint`;
- `acc`;
- `particle`;
- `dumpcommands`;
- `region`;
- `mapfile`;
- `resetnpcdefs`;
- `topbar`;
- `botbar`;
- `colors`;
- `friends`;
- `disconnect`;
- `clearchat`;
- `itemhovers`;
- `objectdef`;
- `noteable`;
- `dumpitems`;
- `resetgraphs`;
- `itemdef`;
- `entitydef`;
- `texture`;
- `textures`.

Their implementations perform exact cache/data diagnostics, definition reload/reset,
region/map inspection, interface inspection/reload/edit operations, item/model diagnostics,
presentation toggles and other client-side development functions.

The class therefore deliberately is **not** called `DeveloperCommandHandler`: its complete
surface includes both ordinary local commands and privilege-gated/debug commands.

## Server-forward queue

The same class owns a static:

`CopyOnWriteArrayList<String>`

Commands can be appended to this queue.

Its flush method retrieves the live Client network writer and, for every queued String:

1. writes packet opcode **103**;
2. writes the command length minus one;
3. writes `command.substring(2)`, removing the leading `::`;
4. finally clears the queue.

That exact behavior links parsing/local handling and server command forwarding in one class.

## Live integration

Exact v308 references `rs/n/a` from the Client and from multiple live interface,
overlay and ScriptPacket paths that generate or process command Strings.

That broad live usage is consistent with one central command-processing gateway.

## Naming boundary

`ClientCommandProcessor` is **0.999**.

The name describes the complete exact behavior without claiming a stripped original source
identifier. A narrower developer-only noun would be misleading because ordinary local
commands and outbound command forwarding are part of the same class.

R172 remains class-only.

## Acceptance boundary

Chat 2 does not promote R172. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_0AC5B516E2D050415E42`.
