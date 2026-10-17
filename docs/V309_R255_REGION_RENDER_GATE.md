# R255 — why R254 game viewport is black: map readiness gate

Audit of canonical R247 Client.java and CacheLoader.java, unchanged by Chat A. Normal region packet **73** requests terrain and landscape archive IDs for surrounding regions via `getRegionFileId(0,...)` / `getRegionFileId(1,...)`. Cache loader enqueues type 3 requests. Only successful completed requests populate `field927[]` terrain and `field975[]` landscape arrays.

`tryEnableDetailedGraphics()` stays blocked (return -1/-2) while requested bytes are absent; it also checks objects walkability (-3) and transition flag `field869` (-4). Only passing this promotes `graphicsMode=2`, constructs the scene via `l()`, and sends outbound map-ready packet 121.

**Ordering:** region packet 73 raises field869; player-sync 81 invokes method1850 and clears field869. R254's 249→73→81 order is correct.

Nine read-only source assertions passed. Actual isolated user home contained main_file_cache.dat (~78 MB) and cache idx0..idx4, but file presence is NOT proof the region indices/bytes (for region 3200,3200 neighborhood) are valid or cache requests completed.

A longer probe retained the same 249,73,81 sequence, observed 84 post-login bytes and region logs, but did not provide a new terrain rendering acceptance image before runner termination. No full-world or native Windows claim.

Next: gather explicit per-region map ID, landscape ID, completion/null bytes, outstanding request count, return code from tryEnableDetailedGraphics in an isolated diagnostic build. Do not guess missing assets or change production client; prove scene readiness before appearance packets. PR #1084 stays draft.
