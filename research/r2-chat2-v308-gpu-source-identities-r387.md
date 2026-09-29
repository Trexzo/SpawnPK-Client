# Chat 2 — GPU plugin source identities R387

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/e/a` -> `CLIENT_CLASS_000900` -> `ColorBlindMode`
- `rs/s/e/c` -> `CLIENT_CLASS_000902` -> `GpuPlugin`
- `rs/s/e/d` -> `CLIENT_CLASS_000903` -> `GpuPluginConfig`
- `rs/s/e/e` -> `CLIENT_CLASS_000905` -> `UIScalingMode`
- review: `SEMREVIEW_9A8F337EA1F3FC2FDD18`

Existing ownership is preserved:

- `rs/s/e/b` -> R185 `GpuPluginPanel`

Exact v308 and RuneLite source/API align on the GPU plugin/config roles and the
ColorBlindMode/UIScalingMode enum identities. Later RuneLite UIScalingMode versions add
HYBRID; v308's exact five-constant set remains authoritative here.

R387 remains non-canonical semantic research only.
