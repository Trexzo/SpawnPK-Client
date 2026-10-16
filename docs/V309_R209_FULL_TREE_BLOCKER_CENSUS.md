# R209 — full candidate Java 11 blocker census

The exact R208 private source snapshot was analyzed as a whole, not from individual compiler samples. All **1,274 source files** are indexed by SHA-256. The real dependency-free Java 11 compiler stderr contains **2,001 errors assigned to 211 source files**; the other 1,063 files have no directly attributed errors in this failed compile, which **does not mean they compile independently or are verified**.

Largest missing package diagnostics: `org.slf4j` 136, `javax.inject` 95, `com.google.inject` 59, `gnu.trove.f.b` 30, `com.google.a.b` 26, `javax.annotation` 23. The obfuscated `com.google.*` packages cannot responsibly be mapped to a guessed Maven dependency. Gradle declares `client/libs/vendored-unidentified.jar`, which is unavailable in the supplied archive. This prevents honest fully resolved `javac --release 11` acceptance.

Local private deliverable `SpawnPK_R209_FULL_TREE_BUILD_AUDIT.zip` includes the full 1,274-source SHA-256/index, exact Java 11 compiler stderr, and reproduction script; its SHA-256 is `41cf65fd84ffbf4a9b6296aa422150cc0d46140cf0f909255a1e0a23ebb8d3ca`. It does not modify source or reduce error count. Do not mark the full source client compiled, do not insert placeholder classes for missing libraries, and do not publish private Java without clearance.

Critical requirements for actual completion: recover exact approved JAR dependencies and original recovered v309 binary witnesses; run dependency-resolved Java11 build; fix remaining authentic Java compiler errors across their complete source owners; compare recovered classes against the original.
