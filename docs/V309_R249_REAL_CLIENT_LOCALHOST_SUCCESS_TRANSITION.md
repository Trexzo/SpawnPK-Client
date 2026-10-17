# R249 — Real source-built v309 client: localhost success response → loading transition

Actual test using Lane A **R247 class-only source-built JAR** (not original executable), archived authentic assets in isolated user.home, and a **resource-only overlay** derived from exact original v309 JAR SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Overlay contains **no original .class** files. The original derived resource paths were supplied using the known R242 32-entry resource mapping plus the loottracker image resource. No changes made to actual production source or user's installed files.

Java21 under Linux/Xvfb (Java 11-compatible rebuilt classfiles); launch flags bound host to `127.0.0.1`, port `43594`, using disposable credentials entered via a real AWT Robot GUI interaction.

## Observed on the real Java client (not synthetic)
- Initial login handshake opcode 14 observed.
- Outgoing login opcode **16**, frame length **106**, received exactly **106** bytes; payload dropped immediately and not persisted. Earlier R235/R242 run measured 105; payload length is **not invariant** across entered credentials.
- Dummy localhost listener returned response `2,0,0` (a test success indication, not authentication logic).
- Client emitted **3 bytes** immediately after response 2.
- Sustained listener held connection for approximately 11 additional seconds, observing **53 aggregate post-success client bytes**.
- Screenshot with live socket shows client left the login form and displayed **"Loading, please wait."** with sidebar icons. No rendered game world or playable world state.
- After listener close, client attempted reconnect; this is not evidence of production transport failure.

## Newly identified runtime input issue
Naive R247 class-only JAR + runtime libs initially failed in `NotificationManager` and `TradingPostSearchPanel` because resources were missing or obfuscated path-mapped. Using R242's explicit resource mapping restored startup. `resources/rs/plugins/loottracker/panel_icon.png` additionally needed a relative resource-path copy. No original project `.class` fallback used. Original client's asset classes were never loaded as code.

## Acceptance boundary
This proves the source-built client can take a synthetic successful-login server response and transition to the loading UI while continuing outbound packet traffic. It does NOT establish valid account authentication, a fully compatible local server, initial player/world packet initialization, native Windows GUI/cache behavior, or original bytecode parity.

Private evidence ZIP `SpawnPK_R249_Real_Client_Login_Success_Evidence.zip` SHA256 `a399a80f3c162fd6012cb4eb4405ea419bd71d9903fe1f749683b689f676940c` includes redacted JSON, screenshots, local listener, isolated GUI Robot test script and logs. No credentials, credential payload or proprietary original game binaries bundled. PR #1084 stays DRAFT. Next work: derive and implement **actual first world-state packet sequence** from verified client source and local server contract, then require a stable game frame rather than login response 2 alone.
