# Chat 2 — GPU source identity R387

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Retained result

- `rs/s/e/a` -> `CLIENT_CLASS_000900` -> `ColorBlindMode`
- review: `SEMREVIEW_73AA6877D6A31AC66FA0`

The enum constants are exactly NONE, PROTANOPE, DEUTERANOPE and TRITANOPE and match the
historical RuneLite GPU source identity.

The former R387 proposals for GpuPlugin, GpuPluginConfig and UIScalingMode were removed
because those exact owners were already reviewed in earlier Chat 2 batches. R387 now
retains only the genuinely fresh class.

R387 remains non-canonical semantic research only.
