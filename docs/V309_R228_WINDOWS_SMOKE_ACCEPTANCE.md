# R228 Lane A — Windows GUI acceptance harness update

**Canonical production source remains R226 merged source; no cache code changed.** R227's rebuild PowerShell script refers to `INPUT_SHA256.json`, but the actual archive contains `R227_INPUT_SHA256.json`; this is a real execution blocker fixed in R228. A new bounded `R228_Windows_GUI_Smoke.ps1` validates pinned binary SHA-256 and original v309 JAR checksum, checks Java 11+, stages original-only resources locally, captures stdout/stderr, per-second process window handles/titles and observed TCP connections; records distinct fields for window observed, external established connections observed, process status and explicit unverified GUI/gameplay/handshake. No automatic whole-desktop screenshot is taken.

**Independent actual Java build replay:** 1,277 sources passed `javac --release 11 -proc:none -g:none`, yielding **1,384** classfiles with zero errors. R228 names, source hashes, dependency hashes and ZIP integrity were validated. The Windows scripts were not executable in this Linux environment and are **NOT Windows-verified**. TCP samples are nonexhaustive; work directory is not guaranteed full filesystem isolation.

Private ZIP `SpawnPK_v309_R228_WINDOWS_GUI_SMOKE_PRIVATE.zip` SHA256 `3605449c8e842ca92fb80347137d2d3b15baaf01b09e56ffb5872ff7ccb78913` contains unchanged full production source, source-built JAR, v309 non-game dependencies, complete Windows scripts, hashes and build log.

Lane B cache-recovery R222 is now reported in Issue #1117; its exact private changed-only overlay was not available in this runtime, so **R228 does not claim to integrate it**. Await the SHA-pinned donor for a proper conflict-free integration. Keep draft pending owner-local Windows GUI screenshot and local-only handshake evidence.
