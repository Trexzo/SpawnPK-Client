# R393 — private v309 plugin startup risk map, static-only

**Repository:** Trexzo/SpawnPK-Client. **Stack base:** R392 draft #1188.
**DRAFT / UNMERGED; Source-M1 private-source release gate CLOSED.**

## Context and core observation

R391 examined original/rebuilt launcher bytecode without class initialization.
R392 found configuration, plugin, filesystem and networking indicators in the
private Java code and confirmed no suitable verified disposable Windows guest
was available for a true GUI launch. R393 advances the investigation by
scoping the synchronous plugin-start path without running any plugin.

The private bootstrap's visible order includes: load/reset configurations,
load plugins, initialize ClientUI, register event listeners, start plugins,
and show the UI. PluginManager.startPlugins() calls startPlugin() through
SwingUtilities.invokeAndWait(). startPlugin() invokes each enabled plugin's
startUp() on the Swing event-dispatch thread. This creates a plausible
freeze/delay boundary, but **does not prove any observed freeze is caused
by plugins**. Active plugin enablement and the actual UI thread state are
not verified in this static audit.

## Genuine owner Windows evidence

The tool verified the isolated private R381 build-kit ZIP against exact SHA-256
902e3b583840073c095ea51c5fe5bee4034340ab92bd19dc7c36f3173f092f96,
and scanned its 1,277/1,277 Java sources in memory without extracting them.
A corrected class-declaration parser excluded an annotation type with a
generic \`Class<? extends Plugin>\` member. Final private result, exit 0:
**30 genuine plugin subclasses; 29 explicit startUp() overrides;
one subclass without an override (NotificationsPlugin)**.

Evidence count of plugins with direct or one-hop constructor lexical indicators:
- Direct startUp() cleanup call: 1 (LootTrackerPlugin)
- One-hop explicitly constructed class with cleanup: 1 (LoadoutsPlugin)
- Direct startUp() persistent-write indicator: 1 (MarketSnipePlugin)
- One-hop constructor persistent-write indicator: 1 (LoadoutsPlugin)
- One-hop constructor read indicator: 2 (LoadoutsPlugin and ProfilesPlugin)
- Direct UI/navigation indicators: 15; one-hop constructor UI indicators: 3
- No explicit network, process execution or blocking-wait indicators found
  in these **limited startup bodies and one-hop constructor bodies**.

Targeted private source inspection complements those lexical indicators:
1. Loot Tracker calls a method that recursively removes a *retired* loot
   history layout and an old key file on startup. It claims not to touch
   the current history file. This is a real potential deletion path, not
   permission to inspect or delete real owner data.
2. Loadouts constructs a panel whose constructor loads/saves settings and
   contains explicit file deletion calls for legacy/default/temporary
   loadout paths. These writes/deletions are not safe to exercise against
   the real home/profile during experimental startup.
3. Profiles constructs a registry that loads the stored account profile
   data. No account contents were read during this audit.
4. Market Snipe calls blacklist seed initialization if needed; this is
   a potential persistent settings write, not a game purchase or task start.

One-hop inspection includes *all constructor bodies with the matching class
name*, not necessarily the exact overload selected at runtime. UI callbacks
present inside a constructor may be counted despite running later. It does
not follow injected service constructors, virtual dispatch, nested helper
methods, fields, superclass initialization, static initializers or plugins'
dependencies. No absence claim is made for those deeper paths. No proof
is made that any particular plugin is enabled or initialized at runtime.

## Public-safe contents and verification

This R393 branch publishes only a generic, SHA-pinned, non-extracting
Java-source-text mapper, 25 tiny synthetic source/ZIP regression tests,
a Windows/Ubuntu Python3.11/Python3.13 workflow and this document.
The 25 tests pass on authorized owner Windows Python 3.12. They include
brace-safe lexical masking, false positive annotations, direct vs one-hop
constructor paths, comment/text-literal exclusion, duplicate class/method
protection, ZIP path/symlink refusal, hash drift and refuse-existing-output.

The generated private JSON report stays under the owner's isolated
R393-Static-Plugin-Startup TEMP directory. Public CI never accesses it,
the private ZIP, original v309 client, compiled candidate, the resource
companion, plugins, caches, login data, user data or credentials.
The public report does not include proprietary source bodies.

**No client entry point executed, no plugin loaded, no GUI/network started,
no production cache/log/account/loadout file modified, no v312 changes.**

## Immediate next acceptance gate

Before any live startup acceptance: verify disposable guest isolation
and no egress, source-independent process and filesystem observability,
read-only placement of private binaries, fresh guest-only config/cache
folders, no mount/write path to live v312, and a bounded start/kill window.
Only inside that guest, consider opt-in startup tracing to distinguish
EDT blocked in plugin startup vs asset/network/cache initialization.
A normal-host run or a scratch \`user.home\` property is not isolation.

Still unproven: original v309 GUI/behavioral equivalence, login/reconnect,
graphics/GPU parity, v312 compatibility, power-loss durability, multi-file
atomicity and safe staging cleanup. KEEP ALL PRs DRAFT AND UNMERGED.
