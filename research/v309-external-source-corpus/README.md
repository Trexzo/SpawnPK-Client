# v309 external recovered-source candidate

This directory records a **research-only intake**, not `recovered-source/v309/` publication. The independent uploaded Java archive is kept outside Git. The original pinned v309 client remains authoritative for binary class and method identities.

- External source archive SHA256: `3a3b84a03f9cc6588a714b03f8b36ae3a7008ce4976de2609841fdf9db9e80ad`.
- Original v309 client SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- Source reports build 309; 1,270 Java files (1,265 under `rs/`), 427 resource files.
- Original JAR contains 10,502 `.class` entries; 28 source Java paths match class paths without renaming. Path coincidence is **not identity proof**.
- The source's edited Loot Tracker document discusses 15 original v309 class paths; those 15 exist in the pinned archive, but documented source mappings are **unaccepted candidates**.
- The source tree does not currently clean-compile: its `libs/vendored-unidentified.jar` is not included; a Java 11, no-original-JAR-fallback preflight stops on missing library/API types.
- The archive contains independently edited plugins and renamed/merged types, so source parity and project class-set equality **must be measured**, not assumed.
- Protected v309 authority remains `ACCEPTED_INCOMPLETE`: 143 unresolved field relationships, 26 descriptor blockers, 0 new accepted identities.

**Next tasks:** independently review exact class/member source crosswalks; reconstruct verified dependencies and compile the entire candidate with zero project-binary fallback; verify every generated class against accepted v309 binary authority; separately run the original v308 Source M1 clean-build publication gate. Do not commit raw decompiled source or place this candidate under `recovered-source/v309/` before all Source Milestone gates actually pass.
