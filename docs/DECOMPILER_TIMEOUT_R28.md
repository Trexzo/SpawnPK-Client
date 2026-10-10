# R28 — bounded decompiler subprocess execution

The shared `spk_recovery.decompiler.run_decompiler` function now accepts an
optional keyword `timeout_seconds` (integer 1 through 3600). The default is
`None`, preserving the previous unlimited-run behavior for existing callers.

For short, privately staged v309 class slices, a bounded run can prevent a
stuck CFR/Vineflower/Procyon JVM from blocking the recovery process.
For example, Python callers may use:

~~~python
run_decompiler(
    private_class_slice, independently_pinned_decompiler,
    expected_decompiler_sha256=actual_tool_sha256,
    engine="cfr",
    out_dir=fresh_private_output_directory,
    timeout_seconds=300,
)
~~~

The checksum preflight remains mandatory. Invalid timeout values are rejected
before any decompiler output directory is created. A subprocess timeout raises
`DecompilerError` with only a stable engine-and-batch timeout code, without
echoing partially captured stdout/stderr that might contain proprietary
class coordinates or recovered code.

A timed-out private output directory may remain for local examination, but
the function does not return a successful decompiler manifest. The caller
must not treat partial generated Java as validated output.

The R27 dual-decompiler orchestrator can opt into this argument in a separate
PR after the independent shared-runner change merges. This R28 change
does **not** impose a timeout on any legacy caller by default.

Original JARs, private class slices and recovered Java must remain local;
this change has no canonical acceptance, lineage mutation or source-publication
capability. Synthetic tests use mocks, no private client source or binaries.
