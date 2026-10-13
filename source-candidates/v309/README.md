# Provisional restored SpawnPK client Java sources — v309

This directory is **not** the canonical complete `recovered-source/v309/src/` release. It contains only individually reviewed, independently recompiled client-source candidates with strict evidence. Every entry is visibly provisional until the **full** client source tree passes the Source Milestone release requirements.

A source may be added only when its original v309 JVM class identity, members and bytecode behavior have been independently checked; unresolved dependencies and postjavac verifier metadata differences must be documented. A single source file never certifies full client compatibility. Original `client.jar`, cache and runtime profiles, decompiler working archives and private experimental binaries do **not** belong in this directory.

Current restored Java source candidate:

- `src/rs/runelite/events/ClientStartUp.java`: user-provided decompiled source, repaired control flow and readable local names. Independently compiled Java9, **33/33** original instructions (including resolved references), one postjavac metadata-only frame rebind to original **3/3** StackMap entries, and rebuilt-class JVM verification. The class still requires inclusion in a complete, dependency-correct original-v309 source release. Reproduction is in `tests/test_private_v309_clientstartup_recovered_source_r131.py`; private binary-backed authority is summarized in `CANDIDATE-CLIENTSTARTUP.json` and `docs/V309_RESTORED_CLIENTSTARTUP_R131.md`.

The final standalone per-build source release, once accepted as complete and redistributable, will be **moved or regenerated** under `recovered-source/v309/src/` with full class/member provenance. No server emulator or reconstructed server source belongs to this client-only area.
