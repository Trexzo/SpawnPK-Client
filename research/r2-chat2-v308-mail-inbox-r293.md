# Chat 2 — exact-v308 mailbox helpers R293

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/c/b` -> `CLIENT_CLASS_000644` -> `InboxMessageListController`
- `rs/n/c/c/c` -> `CLIENT_CLASS_000646` -> `MailAttachmentClaimController`
- review: `SEMREVIEW_CCF718FEE239CB0DE980`
- prior authority retained: R2 `rs/n/c/c/a` -> `MailboxInterface`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 mail contract

`InboxMessageListController` creates **View inbox message** rows, lays them out through the retained interface-layout engine, and applies the exact `UNREAD / READ` state to row color and the unread icon marker.

`MailAttachmentClaimController` owns the attachment claim state machine and switches on the retained `EMPTY / UNCLAIMED / CLAIMED` enum. The claimed state writes the exact text **Items have been claimed!** and toggles the same 321xx mail reward widgets.

The surrounding mailbox root is not re-proposed here: R2 already owns `rs/n/c/c/a` as `MailboxInterface`.

## Boundary

R293 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
