# Chat 2 — R398 notification source-identity correction audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R398 retains **no semantic proposal**.

The attempted R398 proposals targeted:

- `rs/s/n/a` / `CLIENT_CLASS_000935`
- `rs/s/n/b` / `CLIENT_CLASS_000936`

Those exact owners were already reviewed in **R9** as:

- `NotificationAlertsConfig`
- `NotificationAlertsPlugin`

A later recovered semantic source map provides stronger original-source identities:

- `rs/s/n/a` -> `rs.plugins.notifications.NotificationsConfig`
- `rs/s/n/b` -> `rs.plugins.notifications.NotificationsPlugin`

Exact-v308 behavior independently corroborates the source map:

- config group `notifications`;
- exact Notifications plugin descriptor;
- de-aggro / superior-spawn / private-message event handlers;
- direct R14 `Notifier` injection;
- direct config provider pairing.

## Boundary

R398 is therefore a **correction/corroboration audit only**.

It does not create a second owner proposal and does not overwrite historical R9 authority in
this continuation branch. The source-name discrepancy is documented for Main/Core or a
dedicated historical-review correction if that authority is intentionally revised later.

No R398 candidate JSON, semantic-review JSON or deterministic review test is retained.
