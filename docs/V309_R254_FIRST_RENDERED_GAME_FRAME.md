# R254 — actual first rendered source-built v309 game frame

Real Linux/Xvfb test of **unchanged canonical private R247 Java client** with authentic archived assets and **resource-only** original-v309 mappings (no original client .class loaded). Started bound solely to localhost 127.0.0.1:43594 using disposable credentials.

## Server sequence (verified client-derived)
1. Login handshake 14; 8-byte challenge seed; bounded v309 login request opcode 16 with exactly 106 bytes received, RSA-like BigInteger serialization interpreted only in test memory; credentials not logged.
2. Recovered four client ISAAC session keys, server inbound ISAAC words +50; sent response 2,0,0.
3. Sent ISAAC encoded identity 249 (3 bytes), normal region 73 (4 bytes, at coordinates 3200,3200), and minimal player synchronization 81 (variable-short length 2, payload 00 00). The payload means local movement update bit 0, existing-player count 0, no new-player records; packet parsing finished without player size mismatch.
4. Real client emitted region selection/load logs, progressed past loading state and rendered game viewport frame, chatbox, sidebar, inventory, minimap frame and “Walk here” text. Post-success outgoing byte count 82 during bounded capture.

## Resource-path acceptance
Initial graphics initialization failed under software Mesa with shader syntax error and missing skybox input. Remapped **resource-only** `rs/k/` shader/skybox assets into `rs/gpu/` on an isolated resource classpath. Repeated exact probe rendered the game UI. No production Java or installed user files altered.

## Limits
Viewport terrain was still **black** and local player model not rendered. Frame is a *game UI and engine transition*, not a fully loaded region or gameplay. Listener closure later causes the observed reconnect. Native Windows GPU/render and valid root UI 97 were NOT tested. No proof of full server parity or original equivalent source.

Private R254 evidence ZIP SHA256 `78fd6de86a12cd282e9ebefcbd8f8e657eaa6e790e2a1664ee1a0bc185aa813e`: screenshot, redacted listener code/results, scripts and client logs, without credential data or proprietary original assets/JAR.

Next milestone R255: determine why region tiles/models fail to render (map/landscape availability, region readiness, local player appearance and relevant client flags), then hold a persistent localhost connection with a minimally sufficient update stream. Keep PR #1084 DRAFT.