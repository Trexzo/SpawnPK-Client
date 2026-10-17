# Cache R240 staged recovery provenance

R239 could delete a modified staged cache after a crash before promotion, even though the transaction already held its staged-content SHA-256 witness. R240 checks the staged tree against that witness before V2/V3 recovery can delete it. When the content differs, staged files, previous-cache backup and journal are preserved. V1 and pre-witness PREPARING recovery retain legacy semantics.

One production source changed: src/rs/cache/updater/assets/CacheUpdateTransaction.java.
Required R239 preimage SHA256: c7ab5f926fe7a73e36f5ecd133270132767755f4d4a40c92422ee803ede77689.
R240 postimage SHA256: d70ac2ba3c1931ba01f5e77c75e0d3fedaf43b3baff21269c462df4c4a3bd3b5.
Exact source diff Git blob: efe068bd40affc68cc5eb0c3f5a678ae9b274b36.

Actual full private javac --release 11: 1277 Java sources, 1388 classfiles, zero compiler errors. Only one classfile changed vs R239. All 27 offline regressions passed, new R240 31 checks. R227 inherited test fixture adapted TEST-ONLY to expect preservation of modified staged contents followed by explicit remediation/recovery. R239 baseline demonstrably failed the same new test.

Complete SHA-pinned private ZIP SpawnPK_v309_R240_STAGED_RECOVERY_PROVENANCE_PRIVATE.zip SHA256 f8f8f4d0edf220ceac4d57e77d5cd6c2526b67b698c0633c27133d90bd5bbde0. Changed-only overlay SHA256 3ec2db165921cc76ba870e623b1db16d083e9c2392eddab7907ffdf21ffb318a. Full source ZIP SHA256 4b836be08d12f1f73a719c1ed7c05599405a7a299dc8f9f1a721b66830382dbe. Class-only JAR SHA256 9726f770684965bfcf56a74356543a852ee0f38455fef64650f6d9ab3a7dacf1. All nested hashes and ZIP CRC passed.

Chat A's last titled canonical source was R242 with cache R234. Integrate R235->R236->R237->R238->R239->R240 sequentially if hashes still match, changing only CacheUpdateTransaction.java, keeping GUI, downloader, CacheUpdater, login and launcher. This public branch contains a review diff, not a hosted R240 Java test. Native Windows gameplay, hardware power-loss durability and external post-check writer race freedom remain unverified. Keep draft.
