# Chat 2 — exact-v308 texture debug configuration R311

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/l/b/a/b/b` -> `CLIENT_CLASS_000375` -> `TextureDebugConfigLoader`
- review: `SEMREVIEW_9DC3AC6C4324AD9D5A37`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

`rs/l/b/a/b/b` is a static debug-file loader.

It creates `./debug` when the directory does not exist and opens `./debug/textures.txt` through `FileReader` / `BufferedReader`. Before parsing it clears six integer-list fields. The parser ignores `#` comment lines, switches section mode on the exact markers `[textur]`, `[random]`, and `[recolor]`, and parses comma-separated integer values into the lists associated with the active section.

The class has no gameplay-interface construction state. Its only direct bytecode referrer is the nested section-mode helper used by this parser.

## Global-authority correction

An earlier draft of R311 also included `rs/t/b/a` and `rs/t/b/b`. Recovery CI correctly exposed that both were already owned by R249 as `NpcDefinitionDiffDumper` and `ItemDefinitionDiffDumper`.

Those duplicate proposals were removed. This corrected R311 contains only the genuinely unowned `rs/l/b/a/b/b` class and checks its owner, semantic name, and stable ID against every prior review from R2 through R310.

## Boundary

R311 is non-canonical semantic research. `TextureDebugConfigLoader` describes exact-v308 behavior and does not claim the stripped original developer identifier.
