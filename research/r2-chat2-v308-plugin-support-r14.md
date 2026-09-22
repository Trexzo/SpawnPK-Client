# Chat 2 — exact-v308 plugin-support semantics R14

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R14 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R13 review batches.

## Deterministic review result

- candidate classes: **13**
- resolved proposals: **13**
- unresolved: **0**
- review ID: `SEMREVIEW_10B38C13D2C28216E473`
- field/method proposals: **0**

## Loadouts

- `rs/s/k/a` -> `LoadoutsPlugin`

The runtime plugin descriptor explicitly says:

- title: `Loadouts`
- config/group key: `loadouts`
- description: `Set up and switch between loadouts`
- tag/category: `panel`

The class extends the plugin base, creates the `ldt_icon.png` navigation entry and owns
the already reviewed LoadoutFolderPanel.

## Notes

- `rs/s/m/a` -> `NotesConfig`
- `rs/s/m/b` -> `NotesPanel`
- `rs/s/m/c` -> `NotesUndoAction`
- `rs/s/m/d` -> `NotesRedoAction`
- `rs/s/m/f` -> `NotesPlugin`

Exact annotation evidence identifies config group `notes`, config item `notesData`, plugin
title `Notes`, description `Enable the Notes panel` and navigation resource
`notes_icon.png`.

The panel owns a JTextArea and UndoManager. Its adjacent action classes directly execute
UndoManager undo/redo behavior and log exact Notes-specific failures.

## Configuration UI support

- `rs/s/b/g` -> `ConfigurationPlugin`
- `rs/s/b/w` -> `PluginConfigurationRootPanel`
- `rs/s/b/x` -> `IntegerConfigFormatter`

The plugin descriptor title is exactly `Configuration` with group `configs`. The root
panel owns CardLayout navigation between configuration pages and the Plugin Hub. The
formatter extends JFormattedTextField.AbstractFormatter and rejects non-integer values with
the exact validation text `… is not an integer.`.

## Desktop notifications

- `rs/s/n/c` -> `DesktopNotificationService`

This is intentionally not named as a plugin. Exact bytecode implements platform notification
delivery through TrayIcon, `terminal-notifier`, `notify-send` and `osascript`, plus
sound/focus/timing behavior. It is a delivery service consumed by notification-facing
configuration/plugin code.

## Trading Post support

- `rs/s/t/b` -> `TradingPostCurrency`
- `rs/s/t/d` -> `TradingPostListingPanel`
- `rs/s/t/m` -> `TradingPostSearchResultPanel`

The currency enum has exact `GOLD` and `CASH_BAGS` constants with Gold/Bags labels and
matching icons. The listing panel renders one account listing with `Price each:`,
`Received:` and `Sold: … / …`. The search-result panel renders item/value/time data with
relative-time presentation and Trading Post assets.

## Acceptance boundary

Chat 2 does not promote R14. Main/Core may accept any desired subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_10B38C13D2C28216E473`.
