# R205 — bounded grouped Java 11 compilation, real replay

The R204 baseline still contains **379 candidate Java sources compiled together cleanly** and **394 classfiles**, without external dependencies. The earlier 110 individually spawned compiler probes timed out. R205 therefore adds `tools/bounded_source_groups_r205.py`: compile by source-directory group with explicit group and iteration ceilings, retain accepted Java owners only after clean combined javac replay, and write a private source-owner manifest. No original game binary, invented dependency stub, or unchecked progress count is used.

## Local attempted R205 source groups

Against the full 379-source accepted set (not just the 394 classfiles), attempted eight one-source directories under the same `javac --release 11` profile:

| Candidate group | javac errors | Accepted |
|---|---:|---|
| rs/cache/download | 3 | No |
| rs/gpu/template | 2 | No |
| rs/graphics/anim | 6 | No |
| rs/graphics/overlay/icon | 33 | No |
| rs/graphics/overlay/tooltip | 42 | No |
| rs/graphics/overlay/widget | 13 | No |
| rs/graphics/raster | 2 | No |
| rs/gui/gpu | 42 | No |

These failures indicate unresolved source owners in the chosen isolated groups; no files have been modified. The tested eight groups **do not** yield a new source acceptance milestone. Do not claim more than 379 independently compiling source files. This is not exact v309 bytecode parity and still lacks an approved external dependency classpath.

The R205 bounded package group runner and synthetic verification tests pass on Windows and Linux in GitHub Actions. Next substantive required input is the exact verified dependency JAR set from the original build or the original recovered Java source owner graph, rather than arbitrary class patches.
