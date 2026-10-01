# Equivalent-tooling v307/v308 javac backtest

`Invoke-EquivalentToolingV307V308JavacBacktest.ps1` is the local Chat 3 composition boundary for issue #283.

It removes operator drift between the historical v307 and current v308 measurements. The individual runners already record exact `JAVACBIND_*` recovery-tooling commits and the comparator already refuses mismatched commits, but launching the two expensive runs separately can waste time if `main` advances between them.

The orchestrator captures one clean exact `origin/main` commit, runs v307, rechecks that both local HEAD and `origin/main` are unchanged, runs v308, rechecks again, verifies both emitted bindings carry the captured commit, and then immediately invokes the existing redacted cross-version comparator.

Child exit code 3 is a valid evidence state. It means that exact recovery reached the Source-M1 clean-source frontier but is not release-ready yet. When either child returns 3, the orchestrator still requires and compares the private javac diagnostic + clean-rebuild + build-binding evidence, prints the redacted overlap summary, then itself returns 3.

Exit 0 is reserved for the stronger case where both v307 and v308 recovery runs are independently release-ready and the equivalent-tooling comparison also passes.

The wrapper does not propose semantic names, modify source-repair rules, publish private diagnostics, or relax clean-rebuild/release gates.

Default invocation:

```powershell
& "C:\Users\Felix\Desktop\SpawnPK-Client\scripts\Invoke-EquivalentToolingV307V308JavacBacktest.ps1"
```

The current v308 Source-M1 runner may require its normal Windows UAC prompt to enable case sensitivity on its fresh output root.
