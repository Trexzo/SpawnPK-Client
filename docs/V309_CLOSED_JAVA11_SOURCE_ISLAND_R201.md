# R201 — first independently compiling Java 11 candidate-source island

Starting with the private R200 archive (1,274 Java sources), screened for sources with only platform-oriented imports and then compiled **all selected Java classes together** with `javac --release 11 -proc:none -g:none`, without external JARs, original game bytecode, or invented placeholders.

The first pass selected **438 source files**. Javac exposed same-package and related-class dependencies invisible to import-only screening. Iteratively excluding only the files which javac actually rejected (re-running the entire remaining subset) yielded:

| Pass | Sources | Error-owning source files | Error diagnostics |
|---|---:|---:|---:|
| 1 | 438 | 112 | 691 |
| 2 | 326 | 5 | 6 |
| 3 | 321 | 1 | 9 |
| 4 | **320** | **0** | **0** |

The resulting private source-only ZIP `SpawnPK_v309_R201_JAVA11_SOURCE_ONLY_320_PRIVATE.zip` contains these **320 genuine candidate Java files**, a per-file SHA-256 manifest, accepted file list and acceptance history. ZIP SHA-256: `ac32630235593b9db7a9c293d8cd3fdb8d1da05dba54710e71a0e7c5c1d10284`. It is not a replacement for the full 1,274-source private snapshot and establishes no original v309 binary parity. The **remaining full-tree count is still 2,001 errors** in the dependency-free Java11 profile.

GitHub `tools/closed_java11_subset_r201.py` provides a fail-closed locally reproducible fresh-output compilation subset tool; `tests/test_closed_java11_subset_r201.py` plus workflow exercise synthetic Java11 source with rejected external owners. The private game Java text is not uploaded publicly. This is a build acceptance advance, not a newly reconstructed original class.

Next steps: obtain approved exact external dependency artifacts, then progressively extend the independently compiling source subset toward the full 1,274-source tree with a clean classpath. Do not treat the 320 classes as fully reverse engineered or treat absent imports as valid implementations.
