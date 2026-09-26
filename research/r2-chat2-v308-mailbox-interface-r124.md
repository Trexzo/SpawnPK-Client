# Chat 2 — exact-v308 mailbox interface ScriptPacket 31 R124

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R124 is a separate non-canonical class-only review for the direct ScriptPacket handler
whose complete selector surface controls the exact mailbox interface, inbox-message state,
attached-item reward state and mailbox presentation effects.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_2710F7C927590F200A4E`
- field/method proposals: **0**

## Stable ID

`rs/n/c/c/e` -> `CLIENT_CLASS_000649` -> `MailboxInterfacePacketHandler`

R115 registers this class directly as ScriptPacket **31**.

## Independent mailbox-interface authority

R2 already recovered `rs/n/c/c/a` as `MailboxInterface`.

Exact v308 preserves mailbox-specific literals and resources there, including:

- `Inbox (35 / 35)`;
- `Mail Subject`;
- `Delete this message`;
- `No mail message selected!`;
- `No items attached to this message!`;
- `Deposit items to bank`;
- `Deposit items to inventory`;
- `<img=209> Items / Rewards`;
- the `misc/mail` resource family.

ScriptPacket 31 obtains the live controllers owned by that exact interface.

## Complete selector surface

The handler reads one selector in the range **0–7**.

Selectors **0, 1, 2, 5 and 7** operate on the mailbox inbox-list controller
`rs/n/c/c/b`:

- reset/rebuild list state;
- append packet-provided inbox rows;
- update an indexed row's state;
- finalize/recalculate list layout and scroll height;
- clear row selection visuals and optionally select one packet-provided row.

That controller preserves the exact action:

`View inbox message`

and its row-state enum preserves:

- `READ`;
- `UNREAD`.

Selectors **3 and 4** operate on the mailbox attached-item/reward controller
`rs/n/c/c/c`.

Its state enum preserves:

- `EMPTY`;
- `UNCLAIMED`;
- `CLAIMED`.

The same controller writes the exact confirmation:

`@gre@Items have been claimed!`

Selector **6** invokes the generic particle presentation manager twice at the mailbox
reward/attachment panel screen region. It does not mutate a second gameplay or Client
state domain.

No selector branches outside the mailbox UI/presentation responsibility.

## Naming boundary

`MailboxInterfacePacketHandler` is descriptive at **0.998**.

The exact ScriptPacket registration, existing `MailboxInterface` authority, inbox/message
literals, READ/UNREAD row state, attached-item claim states, reward confirmation and complete
selector surface all agree. The English class name is not claimed as a surviving original
SpawnPK identifier.

R124 remains class-only.

## Deliberate exclusion remains

ScriptPacket 32 (`rs/q/a/a/a/a`) remains unnamed. The whole-class coherence requirement is
unchanged.

## Acceptance boundary

Chat 2 does not promote R124. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_2710F7C927590F200A4E`.
