# R360 — source-only diagnostics migration into SpawnPK-Client

**Destination: `Trexzo/SpawnPK-Client`, stacked above R359.** This is a consolidation of *independently written testing/auditing tools* from the separate R351–R355 offline-diagnostics line. **This is not a continuation of the correct repository's earlier R351–R355 source-recovery PR numbering.** Historical labels in filenames are retained solely to preserve test imports and trace provenance.

## Included (reviewed, source-only)

- R351 denied-endpoint guard and synthetic Java contracts; R352 GUI harness source retained for inspection only. Java SecurityManager is deprecated and **not** a trustworthy OS egress boundary.
- R352/R353 supervisor is hard-disabled: `run_r352.execute(...)` always refuses with `R353_ORIGINAL_RUNTIME_DISABLED_PENDING_OS_ISOLATION`; no flag or CI job launches an original game JAR.
- R353 bounded hostname aliases (128 aliases) and event retention, with synthetic fuzz/regression contracts.
- R354 host feature inventory (`r354_inventory.ps1`) and strictly untrusted receipt validation. Test fixture `synthetic_host_disabled.json` **is not a real owner-PC observation**.
- R355 offline Java classfile scanner (`scan_v309_network.py`), nominal method-call path search, separate strict report validator and synthetic classfiles used in tests. The scanner enforces pinned SHA256 and byte length for its CLI original-JAR path. This migration itself never runs that scan on the original JAR.

## What is NOT included

- Any owner-private recovered source archive (1,277 Java files), any original proprietary JAR/cache, any private dependency JAR, machine paths, raw host inventory, personal data, credentials, or logs.
- R350 private owner-PC observation JSON. Its findings are summarized in the migration notes, and its private repo remains unchanged.
- A working game client, live server, verified packet exchange, in-process reconnect, or original GUI acceptance.

## Reproduce source-only checks

```bash
cd research/v309-source-recovery/r360-offline-audit
python -m unittest discover -s . -p 'test_*.py' -v
mkdir -p build
javac --release 17 -d build R351DeniedEndpointAudit.java R351TraceContractTest.java R352OriginalLaunchTrace.java R352GuardInstalledContract.java R353BoundedAliasesContract.java
java -cp build R351TraceContractTest
java '-Djava.security.manager=allow' -cp build R352GuardInstalledContract
java -cp build R353BoundedAliasesContract
python verify_r354.py synthetic_host_disabled.json
```

Never execute an original JAR on a host lacking independently verified OS isolation. Running the *static* R355 scanner against the user's authentic JAR is a separate, explicit local decision, requires the exact SHA pin and does **not** infer runtime destinations from static callsites.

## Provenance and caution

The earlier private R350 line identified a hardcoded endpoint in original `rs.Client.b(int)` and two distinct cache path formulas. R346 saw three Java `checkConnect` denials without destination attribution; DNS permission checks can count without a completed TCP connection. The offline scanner can find possible method callsites, **not** turn those observations into verified network sessions. The data and synthetic tests are independent of R359's reconstructed Java source. Source readability work continues in the R359 stacked branch; this PR does not rename or import game classes.
