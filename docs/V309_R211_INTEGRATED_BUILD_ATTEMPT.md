# R211 — integrated offline/private v309 full-tree build attempt

The private bundle `SpawnPK_R211_INTEGRATED_BUILD_PRIVATE.zip` contains the full 1,274-file R208 Java tree, R210's v382 filtered **non-rs** dependency candidate (which cannot substitute v309 game classes), `SpawnPK_R211_FullTree_Build.ps1`, and source/dependency SHA256 preflight pins. The bundle was ZIP-integrity checked and has SHA256 `4d31e04c0cf2cdec4824be135aa84c95bd699626c91f03f2da42a0ef1ddeea01`.

**Execution design:** On Windows with internet access and javac installed, retrieve a fixed list of real Maven Central artifacts (SLF4J API, Guice, javax.inject, javax.annotation-api, SnakeYAML, Gson, Trove4j, Guava, jsr305, AOP Alliance, Error Prone annotations). Use upstream .sha1 markers where available and record SHA256 of all jars. Extract private source to an isolated fresh working root and compile **all 1,274 sources at once with `--release 11`**. Emit dependency lock, actual javac stderr, result JSON, and **only produce a candidate source-built JAR if the entire build succeeds**. Never launch the production server or hide errors with class stubs. This is not original-v309 bytecode equivalence.

**Local constraint:** Network DNS for Maven Central is unavailable in this execution container, so upstream library artifacts could not be downloaded and a dependency-resolved Java 11 full build cannot truthfully be verified here. The already completed R210 local probe with the verified filtered v382 classes reached 1,799 compiler errors, not zero. Selecting standard Maven libraries is a **hypothesis**, not confirmation they match original obfuscated v309 binary interfaces.

**Four-phase status:** (1) dependency binary extraction partly completed; (2) version-labeled experimental classpath prepared, final closure pending; (3) integrated full-source compile made reproducible but not completed successfully; (4) no fully source-built executable/runtime or original binary parity acceptance. Keep PR draft and do not claim completion.

Do not check proprietary source/JAR contents into public GitHub. Private output is in the conversation.
