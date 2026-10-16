# R224 — legacy applet URL-stream boundary

Continued exact-version v309 private client source reconstruction from R223. Full-tree grep identified a separate HTTP path in `rs/pkg48/Class307.java`: legacy applet URL-stream worker creates a URL from applet codebase + relative resource and invokes `openStream()`. Earlier R222/R223 game-socket guards do not protect this path.

R224 adds `LocalEndpointPolicy.requirePermittedUrl(URL)` and applies it to the real `Class307` applet stream. When `-Dspk.offlineProbe=true`, only explicit loopback HTTP(S) URLs are allowed; public IPs, hostnames requiring DNS, file URLs, and other protocols are refused **before opening a stream**. Without probe mode, original URLs remain allowed. This is not a guarantee of complete network isolation.

Actual full Java11 compilation passed: **1,276** source files, **1,377** generated production classfiles, **zero errors**. Eight separate URL-policy assertions passed, including both loopback address families, public host and IP refusal, hostname refusal, file scheme refusal, and normal-mode preservation. Windows GUI and gameplay were not run.

Complete private source-built delivery: `SpawnPK_v309_R224_LEGACY_URL_BOUNDARY_PRIVATE.zip`, SHA-256 `b7dcd0ce79d2fefb056d61e1e105dd5ebe3021e900269404241c726f7397e8ea`. Rebuilt JAR SHA-256 `60a13a1a0e9bc0702ce80bef16c73e234978b9f211d7ec6157ed9568d5c01fda`. Contains complete Java source, original-version non-game compile and runtime dependencies, SHA-256 pinned Windows rebuild and local-resource scripts, and test code/results. Keep PR draft pending Windows GUI, network exhaustiveness and original behavior parity.
