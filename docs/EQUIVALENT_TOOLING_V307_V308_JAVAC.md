# Equivalent-tooling v307/v308 javac backtest

`Invoke-EquivalentToolingV307V308JavacBacktest.ps1` is the local Chat 3 composition boundary for issue #283.

It removes operator drift between the historical v307 and current v308 measurements. The individual runners already record exact `JAVACBIND_*` recovery-tooling commits and the comparator already refuses mismatched commits, but launching the two expensive runs separately can waste time if `main` advances between them.

The orchestrator captures one clean exact live `origin/main` commit, creates an immutable local bare Git origin pinned to that commit, clones a temporary working repository from the frozen origin, and runs v307, v308, and the comparator inside that frozen repository. Existing nested `git fetch origin main` and HEAD-equality checks are preserved unchanged; they resolve against the frozen local origin rather than live GitHub.

Child exit code 3 is a valid evidence state. It means that exact recovery reached the Source-M1 clean-source frontier but is not release-ready yet. When either child returns 3, the orchestrator still requires and compares the private javac diagnostic + clean-rebuild + build-binding evidence, prints the redacted overlap summary, then itself returns 3.

On a future release-ready child run, the underlying runner currently does not emit a `javac-build-binding.json` because its binding step is part of the blocked diagnostic path. The orchestrator therefore deterministically generates that missing binding from the successful run's private diagnostic + clean-rebuild report using the captured exact tooling commit and pinned build authority, then feeds it through the same comparator verification.

Exit 0 is reserved for the stronger case where both v307 and v308 recovery runs are independently release-ready and the equivalent-tooling comparison also passes.

Live GitHub `main` is allowed to advance while the long run is executing. After evidence is complete, the wrapper refreshes the user's real repo and reports `LIVE_MAIN_ADVANCED=true` plus the newer commit when applicable; that does not invalidate evidence because both measurements were produced from the frozen tooling snapshot. The temporary snapshot is removed on normal exit 0/3 and preserved on unexpected failure for diagnosis.

The wrapper does not propose semantic names, modify source-repair rules, publish private diagnostics, or relax clean-rebuild/release gates.

Default invocation:

```powershell
& "C:\Users\Felix\Desktop\SpawnPK-Client\scripts\Invoke-EquivalentToolingV307V308JavacBacktest.ps1"
```

The current v308 Source-M1 runner may require its normal Windows UAC prompt to enable case sensitivity on its fresh output root.
