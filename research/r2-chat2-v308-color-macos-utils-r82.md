# Chat 2 — exact-v308 Color Gson / macOS window utilities R82

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R82 is a separate non-canonical class-only semantic review batch for two exact runtime
utilities deliberately left unnamed by R21 because that historical-identity pass was kept
narrow.

R82 does not reinterpret the R21 historical claims. Instead, it assigns conservative
behavioral names from exact-v308 contracts and live consumers.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_2C02DF701BB8B1FC8FAF`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/A/f` -> `CLIENT_CLASS_000009`
- `rs/A/o` -> `CLIENT_CLASS_000018`

The same ordering reproduces R21 anchors:

- `rs/A/k` -> `CLIENT_CLASS_000014`
- `rs/A/n` -> `CLIENT_CLASS_000017`

## `rs/A/f` -> `ColorGsonAdapter`

The class directly implements Gson's serializer and deserializer contracts parameterized
with `java.awt.Color`.

Its exact serialization form is a JSON object containing:

- `value` -> `Color.getRGB()`
- `falpha` -> `0.0`

The reverse path requires a JSON object containing `value` and reconstructs a
`java.awt.Color` from that integer.

This is not merely a structurally plausible helper. The client Guice/Gson module
`rs/p/b` constructs this exact class and registers it as the type adapter for
`java.awt.Color` before creating and binding the shared Gson instance used by the
configuration/plugin infrastructure.

The semantic role is therefore fixed strongly enough for the conservative name
`ColorGsonAdapter`.

## `rs/A/o` -> `MacOSWindowUtil`

This class is a static macOS desktop/window helper.

Its JFrame method:

- checks the client's macOS platform enum;
- installs R21 `OSXFullScreenAdapter`;
- calls `FullScreenUtilities.setWindowCanFullScreen(window, true)`;
- preserves the exact diagnostic `Enabled fullscreen on macOS`.

Its other two helpers call:

- `Application.requestUserAttention(true)`
- `Application.requestForeground(true)`

with exact diagnostics:

- `Requested user attention on macOS`
- `Forced focus on macOS`

The live UI shell `rs/ui/f` invokes these helpers for focus/attention behavior and the
GUI frame path also consumes the utility. That active platform plumbing distinguishes it
from an orphan or generic wrapper.

`MacOSWindowUtil` states the proven fullscreen/focus/attention role without asserting a
historical original class name.

## Deliberately still withheld

R82 still does **not** name `rs/A/b` or `rs/A/c`, the package-private cache-loader
helpers owned by R19 `AssetIconManager`. Their behavior is understandable, but they are
thin implementation helpers and naming them does not add enough semantic value to justify
crossing the project's helper-artifact boundary.

## Naming boundary

Both R82 names are conservative semantic recovery names. Neither is claimed as a verbatim
original SpawnPK or RuneLite developer identifier.

## Acceptance boundary

Chat 2 does not promote R82. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_2C02DF701BB8B1FC8FAF`.
