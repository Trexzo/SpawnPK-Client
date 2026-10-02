# Chat 2 — source-proven interface framework roots R406

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Retained proposals

- `rs/n/a` -> `CLIENT_CLASS_000525` -> `DevCommands`
- `rs/n/c` -> `CLIENT_CLASS_000544` -> `Widget`
- `rs/n/d` -> `CLIENT_CLASS_000680` -> `WidgetManager`
- review: `SEMREVIEW_2859E58D002FA464C986`

## DevCommands

The recovered source map identifies `rs/n/a` as `rs.interfaces.DevCommands`.

Exact v308 independently proves the role through its static command dispatcher and literal
developer vocabulary such as `repack`, `gfxdata`, `animdata`, `dumpclip`,
`dumpcommands`, `region`, `mapfile`, `resetnpcdefs`, `dumpitems` and
`resetgraphs`.

This is developer/cache/definition tooling, not the ordinary R172 ClientCommandProcessor.

## Widget

The source map identifies `rs/n/c` as `rs.interfaces.widgets.Widget`.

Exact v308 shows that it:

- extends R56 `RSInterface`;
- stores the shared font/resource array;
- defines an abstract build operation;
- is the superclass for the large custom `rs/n/c/*` SpawnPK interface family.

Existing concrete interface reviews therefore become subclasses of this recovered base.

## WidgetManager

The source map identifies `rs/n/d` as `rs.interfaces.WidgetManager`.

Its exact initializer owns the central `List<rs.n.c>`, resets shared interface/dropdown/task
state, constructs the concrete Widget family and routes each through the same registration
path.

It is distinct from R284 `InterfaceLayoutManager`, which owns relative layout mechanics.

## Withheld source-map entry

`rs/n/b` maps to `ClientModeMap`, but exact v308 is only a compiler-generated static
switch-map over an enum and has no independent live behavior. It remains unnamed.

R406 is non-canonical Chat 2 research only.
