# Chat 2 — classic MouseDetection R407

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

- `rs/b/a` -> `CLIENT_CLASS_000078` -> `MouseDetection`
- review: `SEMREVIEW_CDDB116B7F8DECA23DE1`

## Exact sampler shape

The class implements Runnable and owns:

- two `int[500]` coordinate arrays;
- one synchronized sample index;
- one run/stop boolean;
- one live `Client` reference.

While enabled it samples the exact client mouse-coordinate fields into the paired arrays,
increments the sample count and sleeps **50 ms**.

Samples stop accumulating after 500 entries until the consumer resets/drains the record
state.

## Identity

This is the canonical classic RuneScape mouse-coordinate sampling helper historically known
as `MouseDetection`.

It is distinct from R282 `ClientInputEventQueue`, which queues/coalesces modern pointer
events and wheel/reset boundaries. MouseDetection is the older fixed-rate coordinate sampler.

R407 remains non-canonical semantic research only.
