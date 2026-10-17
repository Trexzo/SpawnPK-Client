#!/usr/bin/env python3
"""R255 read-only client map-readiness gate auditor."""
from pathlib import Path
import json,sys
src=Path(sys.argv[1])
c=(src/'rs/Client.java').read_text()
k=(src/'rs/cache/CacheLoader.java').read_text()
checks={
"terrain_request":"field855.getRegionFileId(0, n9, n16)" in c,
"landscape_request":"field855.getRegionFileId(1, n9, n16)" in c,
"missing_terrain_gate":"this.field927[n] == null && this.field964[n] != -1" in c,
"missing_landscape_gate":"this.field975[n] != null || this.field965[n] == -1" in c,
"completed_terrain":"this.field927[n] = cacheFileRequest.data" in c,
"completed_landscape":"this.field975[n] = cacheFileRequest.data" in c,
"scene_promotion":"graphicsMode = 2;" in c and "this.l();" in c,
"region_transition_cleared_by_player_sync":"this.method1850(this.incomingLength, this.incomingPacket);\n                this.field869 = false;" in c,
"cache_loader_request_processing":"this.processLoadQueue();" in k and "this.checkMissingFiles();" in k
}
assert all(checks.values()),checks
print(json.dumps({"checks":checks,"status":"source-contract-pass","note":"No runtime proof of region file content or completed scene"},indent=2))
