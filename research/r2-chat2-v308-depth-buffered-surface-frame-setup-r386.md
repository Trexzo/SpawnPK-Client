# Chat 2 — depth-buffered surface frame setup R386

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/D` -> `CLIENT_CLASS_000353` -> `DepthBufferedSurfaceFrameSetupTask`
- proposal: `SEMPROP_2AB349ED91BA55879C0F`
- review: `SEMREVIEW_0476EECA2A30E7976B1C`

R85 already fixes the sole owner `rs/l/C` as `DepthBufferedImageSurface`.

The surface's first software-blit path submits `rs/l/D` directly through
`SwingUtilities.invokeLater`.

The task:

- optionally makes the launcher JFrame visible;
- chooses exactly 1134x537 or 1312x800 from the live layout state;
- applies that frame size;
- reads Toolkit screen dimensions;
- centers the JFrame;
- maximizes the wide-layout path when physical screen width is narrower than the requested frame.

The class stores only the synthetic surface owner and has no raster/gameplay/network role.

R386 remains non-canonical class-only semantic research.
