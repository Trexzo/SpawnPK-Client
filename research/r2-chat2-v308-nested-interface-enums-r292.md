# Chat 2 — exact-v308 nested interface enums/models R292

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/A$a` -> `CLIENT_CLASS_000546` -> `ConfirmationDialogType`
- `rs/n/c/J$a` -> `CLIENT_CLASS_000556` -> `EventActivityViewerEntry`
- `rs/n/c/c$a` -> `CLIENT_CLASS_000641` -> `AdventureBookTaskTargetType`
- `rs/n/c/c/b$a` -> `CLIENT_CLASS_000645` -> `InboxMessageReadStatus`
- `rs/n/c/c/c$a` -> `CLIENT_CLASS_000647` -> `MailAttachmentClaimStatus`
- review: `SEMREVIEW_8BB68EEC0B2BF650048C`
- unresolved: **0**
- member proposals: **0**

## Preserved exact identities

The enum constant names survive unobfuscated in exact v308:

- confirmation type: `DEFAULT`, `DESTROY_ITEM`, `YES_NO`
- Adventure Book target type: `ITEM`, `NPC_HEAD`, `OBJ`
- inbox read state: `UNREAD`, `READ`
- mail attachment claim state: `EMPTY`, `UNCLAIMED`, `CLAIMED`

The Event Activity Viewer entry is not an enum, but its parent join is exact: it stores the activity label/icon plus duration/creation time and formats the live remaining countdown consumed by the already-reviewed Event Activity Viewer.

## Boundary

R292 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
