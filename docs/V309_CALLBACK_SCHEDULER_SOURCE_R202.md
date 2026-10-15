# R202 — original v309 callback scheduler

Three SHA-pinned private Java sources for rs/h/b, rs/h/e and rs/h/c rebuild independently with Java 9 source-only compilation. The callback interfaces each declare one abstract method. The scheduler class has seven JVM methods and 121 decoded instructions; original offsets, symbolic references, access flags, member identities, and Code parity match the pinned original class. StackMapTable encoding identity and runtime execution are not asserted.

Private callback source ZIP SHA256: `3c01c0c0e06d077dcd84ebaab8a1507b17562bcf05bfb4e63f4113dc7274604f`.

Private v309 R201 experimental 1291 Java tree SHA256 `033a5a666e2efb279cd04da8e30ca527e9b198719558e3009cd2073fefdb742c`; the new 1294 Java tree is SHA256 `0dfe8e5bd245c6c6b51b562fc310f7730891a3aefaf1e18c97bd10fc6ba6fe39`. All 1291 prior Java sources are unchanged, no invented helper Java is integrated. Same JDK-only full-source compiler: 2367 to 2366 errors; complete client still fails. No original game code executed or published.

The public verifier and synthetic tests require a separate private exact-input replay; hosted synthetic testing does not prove runtime behavior. Source redistribution rights and whole-client compilation remain unverified.