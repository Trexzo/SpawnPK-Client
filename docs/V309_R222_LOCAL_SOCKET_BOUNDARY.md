# R222 — local-only game socket boundary

The R221 client had an opt-in offline HTTP-download mode but no fail-closed restriction on game TCP sockets, and its separate report receiver still connected on port 2456.

R222 adds source `rs/network/LocalEndpointPolicy.java`, updates `rs/Client.java` game socket creation to resolve through it, and disables `rs/report/ReportRequestReceiver.java` in opt-in `-Dspk.offlineProbe=true` mode. A local probe accepts explicit `127.0.0.1` or IPv6 loopback literals; nonlocal hostnames/IPs are rejected **before DNS or connection**. Normal mode retains original server destination behavior. This is scoped to the two identified socket paths and does not establish full network isolation.

**Full compile:** 1,276 Java 11 sources PASS, 1,377 JVM classfiles, zero compiler errors. Independent connection-policy regression: seven offline checks PASS, two normal-mode checks PASS. Actual Windows graphical startup and network-wide monitoring were not performed.

Private full source/JAR/verified Windows tooling ZIP `SpawnPK_v309_R222_LOCAL_SOCKET_BOUNDARY_PRIVATE.zip` SHA256 `7e7ac8037057bb3c0f836e17d7dd4479f5b8e0ba2e2167ee8eaf5845b2af3898`. Source-built JAR SHA256 `a68a11d771a524c429c19e27830db513156c07354235820afef556b8a756570f`. The ZIP includes original-version non-game libraries but no original game classes or font/image assets. Keep PR draft.
