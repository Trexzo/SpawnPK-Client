# Chat 2 — exact-v308 Key Remapping listener R192 correction

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Corrected result

`rs/s/j/b` -> `CLIENT_CLASS_000923` -> `KeyRemappingListener`

- proposal: `SEMPROP_AF69AFED930DB2C735AF`
- review: `SEMREVIEW_FA113A52F76213DB2A58`

R192 originally used the descriptive label `KeyRemappingKeyListener`.

Historical RuneLite source now provides the stronger original class identity
`KeyRemappingListener`, and the exact-v308 structure matches:

- injected KeyRemappingPlugin;
- injected KeyRemappingConfig;
- injected Client/client-thread services;
- modified-key map;
- blocked-character set;
- keyTyped / keyPressed / keyReleased lifecycle;
- camera/F-key remapping;
- Press Enter to Chat state transitions.

Earlier reviews already recover sibling `KeyRemappingConfig` and
`KeyRemappingPlugin`.

The correction strengthens source identity without changing the class coordinate or
behavioral evidence.

R192 remains class-only and non-canonical.
