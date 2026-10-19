# v309 R287 — read-only native-Windows owner readiness

**2026-10-19: Linux-authored and Linux-regression-tested only. Native Windows desktop/GUI acceptance remains NOT TESTED.**

The R285 source-built localhost Cooking range GUI proof passed on Linux/Xvfb. R286 provided a guarded native-Windows acceptance launcher, but has not yet been run on the owner's actual Windows desktop. R287 adds an **independent, source-only readiness probe** before a possible R286 run. It does **not** change or repack the R286 release, modify game Java, alter the owner-installed client, or relax the 1400x900/100%-DPI gate.

## Added source

- **tools/windows/R287-Owner-Readiness.py** — JSON-only, read-only diagnostic with **16 checks**: Windows host, input folder, exact SHA256 for the original **five owner-private input archives plus the R286 source-only release ZIP and the corrected final R286 bootstrap script**, unused safe output destination, Python 3.11+, Pillow, Java and javac 11+, physical 1400x900 primary display with 96-DPI effective system setting, and an unused localhost 127.0.0.1:43594 port. Hashes are streamed rather than reading entire ZIPs into memory.
- **tests/python/r287/R287ReadinessRegression.py** — **20/20 Python unittest cases passed** using disposable dummy archives and injected Win32 observations on Linux. Covers missing/changed pins (including stale R286 bootstrap), wrong display/DPI, busy port, missing compiler, existing or nested output, dangling symlink, missing parent, symlinked owner input, Java-version parsing, and genuine off-Windows refusal.

Run standalone on Windows, with five exact private archives, the R286 source-only ZIP, and the final Invoke-R286-Guarded-Windows.ps1 in the input folder:

~~~powershell
python tools\windows\R287-Owner-Readiness.py --input-dir "$env:USERPROFILE\Downloads" --output "$env:USERPROFILE\Desktop\SpawnPK-R286-Disposable-Acceptance"
~~~

This command **only prints JSON**, with ready=true if the currently observable prerequisites all pass. Exit code is 0 for ready; 2 for any rejection. It never creates the proposed output, changes display settings, extracts an archive, opens the game, or connects to a live server. An output path already present is deliberately rejected.

For a public safe test without any owner assets or Windows runtime:

~~~bash
python tests/python/r287/R287ReadinessRegression.py
~~~

## Interpretation and remaining acceptance boundary

ready=true means *prerequisites only*: it is **NOT** a Windows graphics pass, a Java window-ownership pass, a Cook interaction, or proof of game behavior. The R286 actual runtime still separately validates native desktop/window focus, synthetic loopback packet 132 object 114 to tile (3362,4769), authentic selected region 13386 field1134, map-ready and synthetic reply 253. Its own failure checks remain authoritative. The readiness screen check is conservative: ambiguous display DPI awareness fails closed. A successful port bind is inherently a point-in-time check, not a reservation.

The R278 class-only private JAR SHA256 remains dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd; client production source is unchanged. Original private cache/JAR/dependencies are not committed. No PR merge to main is justified until a *real* owner-side Windows run passes and the original source/provenance gates are resolved.

**Next gate:** native Windows diagnostics (R287) and then guarded R286 GUI acceptance when the owner chooses to run it. If preflight fails, fix the specific environment or mismatch first; do not disable the safety checks to fabricate a pass.

The final R286 standalone bootstrap script is pinned to SHA256 **2186740003afb75df8dd79e2da6a721c121026733dc20ca087973f1d0cd70246**. An older pre-release copy is rejected before anyone attempts the GUI; this corrects the earlier mismatched bootstrap hash circulated during R286 packaging.
