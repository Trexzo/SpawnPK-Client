# Chat 2 — exact-v308 hotspot tooltip helpers R286

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/R` -> `CLIENT_CLASS_000564` -> `HotspotVoteSkipTooltipTask`
- `rs/n/c/S` -> `CLIENT_CLASS_000565` -> `HotspotStatusTooltipTask`
- review: `SEMREVIEW_2C962EAEF0049B63885E`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 evidence

`HotspotVoteSkipTooltipTask` is registered by `EventStatusOverviewInterface` on widget **62153**, the exact **Vote to skip hotspot** control. Its deferred execution sends the exact multiline vote-skip explanation through the live Client tooltip path at the task base's client-relative mouse coordinates.

`HotspotStatusTooltipTask` is registered on hotspot/status widgets **62150**, **62151**, **62152** and **62156**. It displays the live `Client.bS` tooltip string at the same pointer-relative position. It also captures the vote-skip tooltip task and suppresses itself while that task is already pending, proving the two classes are coordinated hover surfaces for the same interface.

## Deliberate exclusion

The generic `rs/n/b/**` scheduler/deferred-task hierarchy remains unnamed. R286 recovers only the exact concrete roles fixed by widget bindings and surviving tooltip behavior.

## Boundary

R286 is non-canonical research only. No semantic acceptance or source rewrite is performed.
