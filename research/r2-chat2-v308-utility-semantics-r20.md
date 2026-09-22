# Chat 2 — exact-v308 utility semantics R20

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R20 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R19 review batches.

## Deterministic review result

- candidate classes: **16**
- resolved proposals: **16**
- unresolved: **0**
- review ID: `SEMREVIEW_E6BE3592C064143A3007`
- field/method proposals: **0**

## Exact-v308 authority

The candidate names are supported by the exact SpawnPK v308 utility implementations.
Several identities are directly preserved by diagnostic text, while the rest are fixed by
their class/interface contracts and method surfaces.

Examples:

- `rs/A/l` -> `LinkBrowser`: exact diagnostics literally contain
  `LinkBrowser.browse()` and `LinkBrowser.open()`.
- `rs/A/r` -> `RunnableExceptionLogger`: wraps Runnable and logs
  `Uncaught exception in runnable {}`.
- `rs/A/e` -> `CallableExceptionLogger`: wraps Callable and logs
  `Uncaught exception in callable {}`.
- `rs/A/h` -> `ExecutorServiceExceptionLogger`: implements
  ScheduledExecutorService and routes tasks through those two wrappers.
- `rs/A/p` -> `QuantityFormatter`: K/M/B/T stack formatting and parsing.
- `rs/A/g` -> `ColorUtil`: color tags, RGB/ARGB conversion, alpha and interpolation.
- `rs/A/s` -> `Text`: CSV, game-tag, escaping, normalization and fuzzy-text helpers.
- `rs/A/t` -> `WildcardMatcher`: converts '*' wildcards into quoted case-insensitive regex.
- `rs/A/j` -> `ImageUtil`: image loading, scaling, flipping, recoloring and transforms.
- `rs/A/d` -> `AsyncBufferedImage`: BufferedImage with deferred completion/repaint callbacks.
- `rs/A/i` -> `HotkeyListener`: Keybind-driven press/release listener contract.
- `rs/A/q` -> `ReflectUtil`: private MethodHandles lookup bootstrap and annotation-cache invalidation.
- `rs/A/q$a` -> `ReflectUtilPrivateLookupHelper`.
- `rs/A/q$b` -> `ReflectUtilPrivateLookupableClassLoader`.
- `rs/A/m` -> `MacOSPopupFactory`: PopupFactory specialization forcing heavyweight popups.
- `rs/A/u` -> `WinUtil`: JNA/Win32 foreground-window helper.

Public RuneLite documentation was used only as a provenance cross-check for these inherited
utility identities. The candidate authority remains the pinned SpawnPK v308 bytecode/source
shape above.

## Acceptance boundary

Chat 2 does not promote R20. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_E6BE3592C064143A3007`.
