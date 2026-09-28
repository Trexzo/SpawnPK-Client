# Chat 2 — exact-v308 mouse position sampler R354

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/b/a` -> `CLIENT_CLASS_000078` -> `MousePositionSampler`
- proposal: `SEMPROP_F5828BD31F4FDCA41B7A`
- review: `SEMREVIEW_FA1B17E0A3980CE98E4C`

## Exact behavior

The class implements `Runnable`.

While enabled it:

1. enters its synchronization lock;
2. if fewer than 500 samples are stored, records:
   - `Client.hP` into one int[500] array;
   - `Client.hQ` into the parallel int[500] array;
3. increments the sample count;
4. sleeps exactly **50 ms**;
5. repeats.

## Client lifecycle

Exact v308 Client:

- constructs exactly one sampler during initialization;
- launches it as a dedicated runnable;
- resets its sample count during session/login reset;
- clears the run flag and drops the reference during shutdown.

## Important boundary

No surviving exact-v308 class directly reads the two sampled coordinate arrays.

Therefore R354 names the proven behavior only: `MousePositionSampler`.

It does **not** assert a surviving telemetry packet, anti-cheat consumer, analytics service or
historical server destination for those samples.

R354 remains non-canonical semantic research only.
