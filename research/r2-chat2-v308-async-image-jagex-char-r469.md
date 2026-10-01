# Chat 2 — exact-v308 asynchronous image/text character utilities R469

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/A/d` -> `CLIENT_CLASS_000007` -> `AsyncBufferedImage`
- `rs/A/k` -> `CLIENT_CLASS_000014` -> `JagexPrintableCharMatcher`
- review: `SEMREVIEW_292A36DD3CBF1DACBFD9`

## AsyncBufferedImage

Exact v308 extends `BufferedImage` and owns:

- a completion flag;
- a list of Runnable callbacks;
- a changed/completion method that drains callbacks;
- immediate asynchronous callback dispatch after completion;
- ImageIcon binding helpers for JButton and JLabel;
- Swing repaint scheduling when image contents become available.

R468-adjacent `rs/A/a` creates and asynchronously fills this type from cached image
sources.

This matches RuneLite `net.runelite.client.util.AsyncBufferedImage`.

## JagexPrintableCharMatcher

Exact v308 extends Guava `CharMatcher`.

It accepts:

- ASCII printable 32..126;
- codepoint 128;
- codepoints 160..255.

That is the exact character-range contract of RuneLite
`JagexPrintableCharMatcher`.

## Boundary

R469 is non-canonical semantic research only.
