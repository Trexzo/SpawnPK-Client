# Chat 2 — R376 duplicate launcher-listener audit

R376 retains **no semantic proposal**.

The attempted owners were already recovered by R280:

- `rs/gui/y` -> `CLIENT_CLASS_000286` -> `RestoreLauncherFromTrayMouseAdapter`
- `rs/gui/z` -> `CLIENT_CLASS_000287` -> `SidePanelToggleAction`
- R280 review: `SEMREVIEW_864C161583CCBDBED781`

The attempted R376 names described the same exact behavior:

- launcher TrayIcon click restores/shows the JFrame;
- the exact `Hide/show side panel` button raises `rs/Client.i`.

Because owner/stable-ID authority already exists, the R376 candidate/review/test artifacts
are removed rather than renamed.

R376 is a zero-retained correction audit only.
