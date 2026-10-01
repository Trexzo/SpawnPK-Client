# Chat 2 — exact-v308 MouseDetection R473

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/b/a` -> `CLIENT_CLASS_000078` -> `MouseDetection`
- proposal: `SEMPROP_1D82DF61AA16CBB5F945`
- review: `SEMREVIEW_CDDB116B7F8DECA23DE1`

## Exact v308 behavior

The class:

- implements `Runnable`;
- owns one `Client` reference;
- owns a synchronization object;
- owns two integer arrays of length **500**;
- owns a running boolean and sample count;
- repeatedly samples `Client.hP` and `Client.hQ`;
- records the pair only while the 500-entry buffer has room;
- sleeps exactly **50 ms** between samples.

This is a periodic mouse-position recorder, not the discrete input-event queue.

R282 already owns the separate `rs/m/a` / `rs/m/a$a`
`ClientInputEventQueue` / `ClientInputEventRecord` family.

## Historical source identity

Public 317/refactored client lineages preserve a class named `MouseDetection` with the same
structural contract:

- Runnable worker;
- Client reference;
- sync object;
- `coordsX` / `coordsY` arrays of length 500;
- running flag and coordinate count;
- 50 ms sampling cadence.

The exact-v308 class is therefore both behaviorally and historically aligned with
`MouseDetection`.

## Boundary

R473 names only the class. No field/method proposals or source rewrite are created.

R473 remains non-canonical Chat 2 semantic research.
