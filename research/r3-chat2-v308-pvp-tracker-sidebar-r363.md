# Chat 2 R3 — PvP Tracker sidebar family R363

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/c/a` -> `CLIENT_CLASS_000260` -> `PvpTrackerSidebarPanel`
- `rs/gui/c/b` -> `CLIENT_CLASS_000261` -> `PvpTrackerMostRecentFightUpdateTask`
- `rs/gui/c/c` -> `CLIENT_CLASS_000262` -> `PvpTrackerPreviousFightUpdateTask`
- review: `SEMREVIEW_388368CF1E9B397616AA`

R357 independently fixes the parent as the exact `PvP Tracker` LauncherSidePanel tab.

The panel contains the literal sections:

- `Most Recent 1v1 Fight`
- `Previous 1v1 Fight`
- `Correct overheads`
- `Spell casts`
- `Damage Dealt`

Its two update methods schedule separate EDT Runnables. The first updates the most-recent
fight label groups; the second updates the previous-fight label groups. Each integer selector
chooses one of the two participant columns, and both tasks switch the user/skull image from
the supplied outcome text and format the three statistic labels.

`rs/gui/c/d` is empty and remains intentionally unnamed.

R363 is descriptive non-canonical semantic research only.
