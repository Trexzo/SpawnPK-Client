# R392 — source-backed prelaunch isolation inventory (launch gate CLOSED)

**Repository:** Trexzo/SpawnPK-Client. **Stack base:** R391 draft PR #1187.
**DRAFT/UNMERGED; Source-M1 private source release gate CLOSED.**
No private source, original JAR, rebuilt JAR, dependency binary, original resources,
owner caches or credentials are committed or attached to CI.

## Why a real game launch is not yet safe

R389 full native Windows compile reproducibility, R390 classloader/resource
visibility, and R391 side-effect-free javap comparison passed, but none of
those tests invoked the actual client. The reconstructed launcher main path
initializes GUI settings, configuration and plugins. The actual game-window
path then creates Client and calls init() followed by start(). Original
and reconstructed main() may also delete old logs. Any runtime test with an
unisolated Windows profile risks modifying data and reaching a live network.

The owner Windows PC was queried read-only: Windows Sandbox executable is
absent at the standard Windows path; querying the optional-feature state
requires elevation. WSL executable is present but reports no installed Linux
subsystem/distro, and Docker Desktop is not installed at its standard path.
Windows Firewall profiles are enabled, but no narrow egress denial was
independently verified for this candidate.

**No game startup should be attempted on this host until real isolation is
available and verified.** Do not mistake environment variables, a different
working directory, proxy settings or an unprivileged Java process for a
network/filesystem isolation boundary.

## Genuine private, nonexecuting R392 scan (Windows)

The owner's existing isolated TEMP copy of the private R381 build kit was
checked against SHA-256
902e3b583840073c095ea51c5fe5bee4034340ab92bd19dc7c36f3173f092f96.
The public-safe R392 tool read **1,277/1,277** Java sources directly
from that ZIP, without extracting files or executing the client.

Aggregate source files containing conservative lexical indicators:
- file_delete: 27; file_write: 31; file_mkdir: 26
- network_connect: 10; dns_local_host: 1
- process_execution: 6; new_thread: 14
- plugin_load: 2; plugin_start: 2; home_directory_access: 2

Examples of known startup-component markers in the private report (counts,
not original source): launcher contains file-deletion indicators; bootstrap
contains home-directory and plugin load/start markers; game client contains
network/local-DNS/thread/process indicators; updater and downloader contain
file-write and network indicators. The tool reports
\`launch_authorized=false\`, \`sandbox_verified=false\`,
\`network_egress_blocked_verified=false\`, and
\`production_paths_isolated_verified=false\`.

**Limitations:** these are lexical matches including possible comments,
inaccessible branches, test support code or unrelated functionality. They
neither establish code reachability nor prove that every operation runs at
startup. A matching path isn't a demonstration of malicious behavior. The
purpose is to identify risk categories that the isolated test environment
must contain, not to classify the client's trustworthiness.

## Public-safe verifier and tests

The verifier checks a SHA-pinned owner-local source ZIP, refuses unsafe or
duplicate paths and ZIP symlinks, imposes per-source and cumulative size caps,
checks source count and critical files, and emits **counts only**. It never
prints raw Java text, endpoint literals or extracted files. Output reports
cannot authorize client startup. Owner-local output is in the isolated
R392-Static-Prelaunch TEMP directory.

The source-free regression contains **19** tiny synthetic ZIP tests, passing
on owner Windows Python 3.12. A 4-way hosted Windows/Ubuntu Python 3.11/3.13
matrix runs exclusively against synthetic source fixtures.

## Requirements for a future real startup acceptance

Before actual execution, require an isolated disposable Windows guest/VM
that is verified to have networking disabled or all outbound traffic blocked
independently of Java; no host user home, original client, resolver, updater
or cache directories mounted writable; only a purpose-built read-only
staging folder containing SHA-verified candidate/dependency/resources;
reproducible log capture within the guest; and a bounded, killable process.
Verify and record the guest's filesystem and network controls *before*
launch, and stop/refuse on any missing check. Never assume a Windows Sandbox
installation based solely on an executable's existence.

Do not call Launcher.main, Launcher.b, Client.main, plugin bootstrap or
any other client initialization method as a preflight. No real GUI, login,
network, updater, login/reconnect, v312 compatibility, power-loss durability,
safe stage cleanup or original-v309 behavioral parity has been tested by R392.
No production files modified and no source release authorized.
