# Chat 2 — exact-v308 Event Activity Viewer refresh task R285

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/L` -> `CLIENT_CLASS_000558` -> `EventActivityViewerRefreshTask`
- review: `SEMREVIEW_55FF3724E2430093649C`
- existing surrounding authority retained:
  - R2: `rs/n/c/O` -> `ActiveEventsInterface`
  - R127: `rs/n/c/P` -> `ActiveEventsInterfacePacketHandler`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 evidence

`EventActivityViewerRefreshTask` is registered by the retained `EventActivityViewerInterface` for interface 30072 at a 500 ms interval. Every run walks that interface's activity rows and refreshes the corresponding text widgets beginning at 30333.

The originally drafted R285 also described `rs/n/c/O` and `rs/n/c/P`, but those owners already have prior semantic authority. They are intentionally not re-proposed here. R285 contributes only the previously unowned refresh task.

## Boundary

R285 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
