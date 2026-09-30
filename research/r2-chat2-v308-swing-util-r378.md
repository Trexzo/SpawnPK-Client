# Chat 2 — R378 duplicate SwingUtil audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R378 retains **no semantic proposal**.

The attempted exact-source recovery:

- `rs/gui/M`
- `CLIENT_CLASS_000197`
- attempted name `SwingUtil`

collides with the already-retained R180 semantic name `SwingUtil`.

The repository-wide uniqueness guard correctly rejects two distinct class owners sharing the
same semantic class name.

## Evidence retained

The attempted R378 evidence remains useful as corroboration for the class role:

- exact-v308 `rs/gui/M` is stateless Swing utility infrastructure;
- it configures Swing/UI defaults and LookAndFeel;
- it creates/stylizes buttons and popup-menu items;
- it creates system-tray icons;
- it preserves the literal `Unable to add system tray icon`;
- it constructs R371 `SwingUtilTrayIconMouseListener`.

Historical RuneLite/OpenOSRS source fingerprints strongly match
`net.runelite.client.util.SwingUtil`.

That evidence is not enough to override the project-wide one-name/one-owner invariant while
R180 already owns the same semantic name.

## CI failure

R383 CI run `36682610648` exposed the inherited duplicate:

`duplicate class semantic name SwingUtil: R180 and R378`

R379-R383 per-batch uniqueness tests then failed transitively because R378 appeared in their
prior-review corpus.

## Correction

The R378 candidate JSON, semantic-review JSON and deterministic test are removed.

This file remains as a zero-retained duplicate/source-corroboration audit only.

R378 performs no semantic acceptance or source rewrite.
