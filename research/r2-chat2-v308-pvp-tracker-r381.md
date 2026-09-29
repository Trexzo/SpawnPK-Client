# Chat 2 — live PvP Tracker Swing family R381

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/c/a` -> `CLIENT_CLASS_000260` -> `PvpTrackerPanel`
- `rs/gui/c/b` -> `CLIENT_CLASS_000261` -> `PvpTrackerRecentFightUpdateTask`
- `rs/gui/c/c` -> `CLIENT_CLASS_000262` -> `PvpTrackerPreviousFightUpdateTask`
- review: `SEMREVIEW_CA3396D53379158FEF43`

## Live tab ownership

The exact `rs/gui/J` launcher side panel constructs `rs/gui/c/a` and adds it to the live
JTabbedPane under the exact tab title:

`PvP Tracker`

The panel itself contains exact presentation strings for:

- `Most Recent 1v1 Fight`
- `Previous 1v1 Fight`
- `Correct overheads`
- `Spell casts`
- `Damage Dealt`
- `Type ::pvptracker to view overlay in-game`

## Swing update tasks

The panel exposes two update entry points.

The first creates `rs/gui/c/b` and dispatches it through
`java.awt.EventQueue.invokeLater`. It updates the recent-fight label group.

The second creates `rs/gui/c/c` through the same EDT path and updates the previous-fight
label group.

Both tasks choose left/right label targets by side selector, set death/skull icons and
format the four supplied strings into the corresponding Swing labels.

## Withheld neighbor

`rs/gui/c/d` remains unnamed because exact v308 shows only an empty Object subclass with
no fields, methods or recoverable semantic role.

R381 remains non-canonical Chat 2 semantic research only.
