# Chat 2 — exact-v308 PvP Tracker helper recovery R184

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R184 is a separate non-canonical class-only review for the final two unnamed classes in the
exact `rs/s/q/*` PvP Tracker package after R183 recovered `FightPerformancePanel`.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_6EF898C70F9EB88FC1F1`
- field/method proposals: **0**

## Stable IDs

- `rs/s/q/b/b` -> `CLIENT_CLASS_000955` -> `PvPTrackerSectionHeaderPanel`
- `rs/s/q/c` -> `CLIENT_CLASS_000956` -> `PvPTrackerFilterDocumentListener`

## PvPTrackerSectionHeaderPanel

Exact v308 `rs/s/q/b/b` directly extends `JPanel`.

R12 `PvPTrackerPanel` constructs it twice:

- `new ...("Current Fight", false)`;
- `new ...("Fight History (Filter by Usernames:)", true)`.

The constructor accepts only the title plus the boolean mode. It installs a centered white
title label, RuneLite panel styling and fixed 350px maximum width.

When the history mode is enabled, it installs exact popup actions:

- `Copy Fight History Data`;
- `Import Fight History Data`;
- `Remove All Fights`.

The import path preserves:

- `Enter the fight history data you wish to import:`;
- `Import Fight History`.

The destructive reset preserves:

- `Are you sure you want to reset all fight history data? This cannot be undone.`;
- `Warning`.

All actions call only the reviewed `PvPTrackerPlugin` singleton.

The proposed name is therefore deliberately descriptive: this is the reusable section-header
panel around the current-fight and fight-history sections, not a claim about a lost original
developer identifier.

## PvPTrackerFilterDocumentListener

Exact v308 `rs/s/q/c` implements `DocumentListener`.

It owns exactly:

- one `PvPTrackerPlugin`;
- one filter `JTextField`;
- one `PvPTrackerPanel`.

`insertUpdate`, `removeUpdate` and `changedUpdate` all delegate to the same private
update method.

That method:

1. reads the current text field value;
2. sends it to the PvP Tracker plugin's filter-update method;
3. triggers the PvP Tracker panel refresh path when applicable.

The upstream PvP Performance Tracker panel independently uses a `DocumentListener` on the
fight-filter field to propagate filter text into plugin state and schedule panel rebuilding.
That corroborates the responsibility, but no original standalone helper-class name survives.

## Confidence boundary

- `PvPTrackerSectionHeaderPanel`: **0.998**
- `PvPTrackerFilterDocumentListener`: **0.999**

Both names describe exact whole-class behavior. Neither is claimed as an original source name.

## Acceptance boundary

R184 remains class-only and non-canonical. Main/Core may accept either proposal only through
an explicit `semantic_acceptance_spec` bound to `SEMREVIEW_6EF898C70F9EB88FC1F1`.
