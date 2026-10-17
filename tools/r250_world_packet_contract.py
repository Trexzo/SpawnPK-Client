#!/usr/bin/env python3
"""Read-only v309 post-login packet contract audit. No binary fallback."""
from pathlib import Path
import re, json, hashlib, sys
root=Path(sys.argv[1])
client=(root/"rs/Client.java").read_text()
lengths=(root/"rs/io/IncomingPacketLengths.java").read_text()
table={int(k):int(v) for k,v in re.findall(r"incomingLengths\[(\d+)\] = (-?\d+);", lengths)}
assert len(table)==257 and set(table)==set(range(257))
checks={
 "login_success":"if (n2 == 2)" in client and "this.finishLogin();" in client,
 "cipher_decode":"this.incomingOpcode - this.incomingCipher.method0() & 0xFF" in client,
 "variable_byte_length":"if (this.incomingLength == -1)" in client,
 "variable_short_length":"if (this.incomingLength == -2)" in client,
 "region_branch":"this.incomingOpcode == 73 || this.incomingOpcode == 241" in client,
 "region_normal_decode":"n37 = this.incomingPacket.method761();" in client and "n38 = this.incomingPacket.method3348();" in client,
 "player_update":"if (this.incomingOpcode == 81)" in client,
 "npc_update":"if (this.incomingOpcode == 65)" in client,
 "player_identity":"this.incomingOpcode == 249" in client,
 "region_base":"baseX = (this.field856 - 6) * 8;" in client,
 "login_state":"gameStateChanged.setGameState(GameState.LOGGING_IN);" in client,
}
assert all(checks.values()),checks
ids=(73,241,81,65,249,97,176,185)
actual={str(k):table[k] for k in ids}
assert actual=={"73":4,"241":-2,"81":-2,"65":-2,"249":3,"97":2,"176":10,"185":2}
print(json.dumps({"assertions":len(checks)+1,"client_sha256":hashlib.sha256(client.encode()).hexdigest(),"packet_lengths_sha256":hashlib.sha256(lengths.encode()).hexdigest(),"packet_lengths":actual,"source_contract_only":True},indent=2))
