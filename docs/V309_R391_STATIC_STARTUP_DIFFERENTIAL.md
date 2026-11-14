# R391 — original v309 vs reconstructed startup, static differential

Repository: Trexzo/SpawnPK-Client. Base: R390 draft PR #1184.
**KEEP DRAFT / UNMERGED. Source-M1 private-source release gate CLOSED.**

## Why the next step is not to launch

Owner Windows JDK21 full-source build reproducibility has already been evidenced
in the isolated R389 build. R390 confirmed class loading and resource lookup
*without initialization*. Those results do not authorize client startup.
The recovered launcher performs configuration and plugin initialization in
main(), and the GUI startup method creates the game client, calls its init(),
then starts it. These steps may create/delete files, display windows, load
external components, start threads, and later access a network.

## Actual owner-private offline bytecode evidence (not hosted CI)

Rechecked SHA-pinned original v309 JAR:
ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38.
The native-Windows rebuilt candidate:
ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3.

JDK21 javap disassembled original and candidate rs.gui.Launcher and rs.Client
*without running or initializing any client class*. Independently inspected
method-level Java bytecode, then replayed the new SHA-pinned R391 static
CLI against those exact two local archives. R391_READ_ONLY_STARTUP_AUDIT PASS.

Observed original -> candidate:
- Launcher.main(): 33 -> 25 invocation instructions, 6 -> 7 conditional branches.
- Launcher.b(): 97 -> 99 invocation instructions, 9 -> 10 conditional branches.
- Client.init(): 4 -> 4 invocation instructions.
- Both Launcher.b() methods invoke Client.init() before Client.start().
- Both Client.init() methods invoke InetAddress.getLocalHost().
- Both launcher main() methods may call File.delete() during log maintenance.
- The original main() invokes System.setOut and System.setErr. The candidate
  does not: the recovered-source log redirection is commented out.
- The candidate main() contains an additional configuration-controlled branch
  around the log-maintenance section, absent from the original at that point.
  The recovered configuration sets the guard true by default under ordinary
  non-developer mode, so the deletion exposure remains relevant.

Original helper class names and bytecode are omitted from this public report.
Instruction counts are **not** proof of semantic or behavior parity; Java
compiler, classfile version, remapping and intentional changes influence them.

## Public CI scope

Only four public-safe files: generic Python static javap verifier, 14 synthetic
parser/JDK regressions, hosted Windows/Ubuntu CI and this report. Tests compile
tiny Java fixtures and run *javap* on synthetic JARs. No original or rebuilt
proprietary client archive, Java source, plugin, resource companion, cache or
credential is uploaded. Source-backed private result remains on owner Windows.

## Required safety gates before any real startup

An optional future startup test requires a freshly isolated scratch home,
verified config/plugin/cache paths, denied game/update/network egress and
bounded lifetime, complete process observability, and a clear no-production-
writes policy. The above audit neither proves these controls nor performs an
isolated startup. Never invoke Launcher.main(), Launcher.b() or Client.main()
as a "read-only smoke test".

No original binary parity, actual GUI/login behavior, v312 compatibility,
safe staging-file deletion, physical power-loss durability or multi-file
atomicity proven. No live client, updater, original v309 binary, server or
owner cache modified. KEEP DRAFT AND UNMERGED.
