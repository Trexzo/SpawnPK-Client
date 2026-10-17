# R259 — Model queue runtime transition observed

Actual isolated Linux/Xvfb reconstructed Java client using R256 game-frame/region probe, with temporary **CacheLoader.java** and **Model.java** diagnostic overlays. Both overlays compile successfully via Java11 release mode against verified source-built R256 classes. **No production client modifications**.

Eight representative R257 missing-model IDs: 1124, 1139, 1517, 1405, 1406, 1407, 1409, 2259.

Actual runtime event counts in most recent trace: **638 request calls**, **24 cache hits**, **24 completed deliveries**, **24 Model.method1700 installation calls**. All eight model IDs observed at all three cache-hit/delivery/install phases. Repeated polling before resolution explains many repeated requests; this does not imply 638 distinct missing models.

For IDs 1124 and 1139, 735 lookup logs included **462 null** and **273 present** checks; final checks were `osrs=false direct=present`. This directly confirms **at least two** previously missing model headers became available in the ordinary model-header table during the real client session.

No proof all landscape model IDs are installed or that scene transitioned to `graphicsMode=2`. R259 focuses on pipeline health, not game-world acceptance. Native Windows runtime unverified.

Private evidence ZIP `SpawnPK_R259_Model_Queue_Runtime_Evidence.zip` SHA256 `d886f2fecfa2eae54b7386cdaae9868692b8ca828114109cee4ae2caabe9e85b` contains redacted logs, source overlays, compilation log and event summary. Next: identify remaining unresolved model IDs at late steady-state and capture `tryEnableDetailedGraphics()` return after the last model delivery, before considering production fixes. Keep PR #1084 DRAFT.