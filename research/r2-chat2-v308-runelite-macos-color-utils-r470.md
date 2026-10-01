# Chat 2 — exact-v308 RuneLite macOS/color utilities R470

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/A/f` -> `CLIENT_CLASS_000009` -> `ColorTypeAdapter`
- `rs/A/n` -> `CLIENT_CLASS_000017` -> `OSXFullScreenAdapter`
- `rs/A/o` -> `CLIENT_CLASS_000018` -> `OSXUtil`
- review: `SEMREVIEW_AF256C9D6CBE6AB68DF1`

## ColorTypeAdapter

Exact v308 implements Gson serialization/deserialization for `java.awt.Color`.

The serialized object uses:

- `value` -> `Color.getRGB()`
- `falpha` -> `0.0`

The matching RuneLite HTTP API adapter/tests preserve the same JSON shape and class
identity.

## OSXFullScreenAdapter

Exact v308 extends Apple's `FullScreenAdapter`, owns the target Frame and adjusts its
extended state on fullscreen enter/exit.

Surviving diagnostics explicitly describe entering/exiting fullscreen mode.

## OSXUtil

Exact v308 provides macOS-only helpers for:

- enabling native fullscreen;
- installing the fullscreen adapter;
- requesting user attention;
- forcing application focus/foreground.

The literal `Enabled fullscreen on macOS` and its surrounding implementation match
historical RuneLite `OSXUtil`.

## Withheld adjacent image manager

`rs/A/a` and its key/cache-loader helpers remain unnamed in R470. The first cache is
strongly ItemManager-like, but exact v308 also owns a second `String,int` asynchronous
image cache not matched to the upstream ItemManager source. The class identity is therefore
not being forced.

R470 remains non-canonical semantic research only.
