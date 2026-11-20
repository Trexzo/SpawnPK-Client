# R437 — exact first-owner and invalid-root rejection receipts

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R436 draft PR #1232  
**Status:** DRAFT / UNMERGED / PUBLIC ACCEPTANCE ONLY; private owner execution and release remain blocked.

## Two remaining acceptance false-positive paths

1. R434's bounded initial Java holder reader returned `line.strip()`. This collapses `" ACQUIRED\n"`, `"ACQUIRED \n"`, and even EOF without a terminating newline into the literal `ACQUIRED`; R422 could incorrectly treat malformed stdout as evidence that an owner JVM holds the OS writer lease.
2. R422's negative-root test accepted any nonzero exit whose **stderr contains** `R422_REFUSE_NON_SYNTHETIC_TEMP_ROOT`. A stack trace or fabricated diagnostic containing that string, without the expected validated refusal, could count as a successful fail-closed path test.

## R437 code

- The initial holder announcement remains subject to a 10-second deadline and child-process cleanup inside the existing `try/finally` from R434. The reader now uses `readline(64)`, so a long unterminated line cannot accumulate without bound. It accepts only a complete LF or CRLF token `ACQUIRED`, `REFUSED_OWNER`, or `REFUSED_PREPARE`; all other output raises an explicit refusal. The caller's original `line == "ACQUIRED"` test stays mandatory.
- The **public** R422 Java acceptance harness converts only its existing `R422_REFUSE_NON_SYNTHETIC_TEMP_ROOT` exception into a stable negative test response: exactly one stdout line and process exit code **64**. All other exceptions retain their original failure behavior. No normal write, delete, or existing Store method is modified.
- The R422 runner now requires **both** exit 64 and `exact_stdout_protocol(stdout, "R422_REFUSE_NON_SYNTHETIC_TEMP_ROOT")`. An error substring in stderr is no longer sufficient. This is a harness-specific negative test code, not a general client exit code.
- R422's exact 17 named checks, 73 real Store assertions threshold, SHA pins, R435 owner status strictness, R436 exact assertion parsing, R415/R417 retained journal evidence/write fences, and R432 private acceptance/release guard remain unchanged.

## Tests and limitations

Thirteen R437 public tests exercise full and refused owner messages, whitespace/prefix/negation/unterminated/oversize output, bounded startup, exact invalid-root exit/receipt, and actual JDK21 compilation of the checked-in public R422 Java harness using an **invented** Store stub. The Java test checks a TEMP parent is refused with exit 64, while a correctly named invented TEMP child reaches the stub's explicit `REFUSED_PREPARE` path. All test work uses ephemeral fabricated processes and test trees; no private game bytecode, real history or installed client is loaded.

The Windows/Ubuntu × Python 3.11/3.13 workflow also re-executes inherited R436/R435/R434/R433/R432 suites. **Do not claim success until final-head hosted CI reports PASS.** The owner-private R424/R425/R432 compile and cross-JVM acceptance, R427–R431 real async Store/Plugin integration, live Swing lifecycle, and deployed v312 runtime test remain unverified. Never clear persistent intent/ack/stage evidence or reopen writes on a public harness pass. No merge or release authorized.
