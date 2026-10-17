# Cache R244: witnessed ownership of PREPARING stage

Chat B's R243 helper could erase files added or rewritten in a PREPARING stage on restart even if the live original cache still existed. R244 verifies each staged file/directory against the live original, accepting automatic cleanup only for a byte-identical subset. In-process failed download/extraction cleanup is explicitly unchanged. Legacy V1/V2 PREPARING recovery also remains compatible.

Only production source changed: src/rs/cache/updater/assets/CacheUpdateTransaction.java.
R243 SHA256 preimage: 874428025bf3b6f71d66fc81ead70ef04e2322dbd3290a8666532d92dac39051.
R244 SHA256 postimage: 78b2de68d0ea781cac34cc4139dbd6f1f26623429a465385ce9cabc732f8b8ed.
Exact review diff Git blob: 8c8deee13f063c2cda94dea0d74d92b526f3f2f9.
Public new regression Git blob: 0cb89cb6a50e7acb00bcfb0f75becca791e28ed2.

Private full javac --release 11: 1277 Java source, 1388 production classfiles, zero errors; only one production .class differs from R243. All 31 offline Java regression programs passed, including 30 checks in the new R244 fixture. One inherited R238 test was adapted TEST-ONLY for manual staged-content reconciliation.

Full deterministic private ZIP SHA256: 1f6be244d8148ad17c3f23898704e8e0057db88ed4f844d4db2ebe3efb3caafc.
Incremental changed-only ZIP SHA256: 13825f6179d9d852478ef15595d5f132ad4817b554aca5f5fdb6fb1a373b5729.
Direct R234-to-R244 cumulative one-file ZIP SHA256: 084ecdf8d05b2adfc3052aedbb60fd317f211d4258af1b687b12bff8a17a0f55.

All eleven R234-R244 complete donor source snapshots have the same other 1276 Java files. The cumulative PowerShell installer requires EXACT R234 helper preimage bc08aff2ddd3948f5ea8c248100234a39ee03cafd66b24e27b48c85e91aa2cad before replacing this one source file; it backs up and verifies R244 postimage, and stops on unknown hashes. Do not overwrite Chat A's other files or GUI, shaders, downloader, networking or world-rendering work. Independently rebuild and test its current full source after integration.

GitHub holds review diff and Java test source, not full private R244 compiled-helper CI. Native Windows game, real power-cut, and hostile post-hash races remain unverified; keep draft and do not merge.
