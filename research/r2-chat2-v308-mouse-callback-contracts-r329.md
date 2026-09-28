# Chat 2 — mouse sampler and callback contracts R329

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/b/a` -> `CLIENT_CLASS_000078` -> `MouseCoordinateSampler`
- `rs/h/b` -> `CLIENT_CLASS_000290` -> `ClientCallback`
- `rs/h/e` -> `CLIENT_CLASS_000293` -> `ClientLoopCallback`
- review: `SEMREVIEW_4807A13BA5B947AAF223`

## MouseCoordinateSampler

The class is a dedicated background Runnable.

It owns paired 500-entry integer arrays and, every 50 ms, samples the two live Client mouse
coordinate fields into the arrays under a lock. Client constructs and schedules exactly one
instance, resets the sample index during session setup and clears the running flag during
shutdown.

No click/button or packet behavior is mixed into this class.

## ClientCallback

`rs/h/b` is a one-method interface:

`void invoke()`

It is used broadly by Client, R281 CustomMenuEntry/CustomMenuManager and multiple UI/plugin
classes.

The two exact-v308 callback registries (`rs/h/a` and `rs/h/c`) both queue/key these
callbacks, invoke them and clear the one-shot registrations.

## ClientLoopCallback

`rs/h/e` is a one-method interface:

`boolean loop()`

The callback registries invoke keyed loop callbacks every processing cycle. Returning false
removes the key; returning true retains it for another cycle.

## Duplicate-manager boundary

`rs/h/a` and `rs/h/c` implement the same callback-registry behavior with different class
identities and overlapping consumers. R329 does not arbitrarily choose one as the canonical
manager semantic owner.

R329 remains non-canonical semantic research only.
