# Chat 2 — exact-v308 mail inbox subsystem R293

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/c/a` -> `CLIENT_CLASS_000643` -> `MailInboxInterface`
- `rs/n/c/c/b` -> `CLIENT_CLASS_000644` -> `InboxMessageListController`
- `rs/n/c/c/c` -> `CLIENT_CLASS_000646` -> `MailAttachmentClaimController`
- review: `SEMREVIEW_F8CEB5576A69E962C07D`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 mail contract

`MailInboxInterface` preserves the inbox/message surface directly: **Inbox**, **Mail Subject**, sent/expiry timing, delete-message controls and attached **Items / Rewards** actions for depositing to inventory or bank.

`InboxMessageListController` creates **View inbox message** rows, lays them out through the retained interface-layout engine, and applies the exact `UNREAD / READ` enum state to row color and the unread icon marker.

`MailAttachmentClaimController` owns the attachment claim state machine and switches on the retained `EMPTY / UNCLAIMED / CLAIMED` enum. The claimed state writes the exact text **Items have been claimed!** and toggles the same 321xx mail reward widgets.

## Boundary

R293 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
