# Chat 2 — exact-v308 DevToolsOverlay R245

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_DD0773962BE6A2B72211`
- field/method proposals: **0**

## Stable identity

`rs/s/c/b` -> `CLIENT_CLASS_000888` -> `DevToolsOverlay`

The stable slot is fixed by the contiguous DevTools package sequence:

- `rs/s/c/a` -> `CLIENT_CLASS_000887` -> `DevToolsConfig`
- `rs/s/c/b` -> `CLIENT_CLASS_000888`
- `rs/s/c/c` -> `CLIENT_CLASS_000889` -> `DevToolsPlugin`

## Exact role

The class:

- extends reviewed `Overlay`;
- implements reviewed `ClientKeyListener`;
- is injected with the reviewed `DevToolsPlugin` and `DevToolsConfig`;
- owns DevTools overlay/input state;
- renders polygon/text diagnostics for interface and drag state;
- preserves diagnostic text fragments including `@gre@m:`, `@mag@intf:`, and `@red@drag:`;
- handles DevTools keyboard controls through `keyPressed`.

Historical RuneLite source independently preserves a dedicated `DevToolsOverlay` class in the same DevTools subsystem, separate from the plugin/config/panel and widget-inspector surfaces.

Confidence is **0.999**.

## Acceptance boundary

R245 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
