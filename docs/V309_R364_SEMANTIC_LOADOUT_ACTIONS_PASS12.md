# R364 — v309 semantic loadout action readability (pass 12)

**Correct repository:** Trexzo/SpawnPK-Client. Stacked on R363 draft PR #1156. Recovered source and dependencies remain owner-private and are NOT committed here.

## Reversible, source-grounded rename

Input is the pinned R363 private 1,277-Java source archive, SHA-256 035837ec988fff706bbfb241e593277e8a5c39c448821982667a33b26f990450. All archive member hashes are checked against its private R363 manifest.

R364 performs **3 class and 2 method renames** (14 Java identifier occurrences across 5 source files). No Java method body, serialization format, network routine or production path is changed.

| Old Java name | Inferred new name | Source evidence |
| --- | --- | --- |
| SaveLoadoutAction | DeleteLoadoutConfirmAction | Delegates to named-loadout removal and closes dialog |
| MoveFolderDownAction | MoveLoadoutDownAction | Uses selected loadout index +1 and swaps list entries |
| MoveFolderUpAction | MoveLoadoutUpAction | Uses selected loadout index -1 and swaps list entries |
| LoadoutFolders.saveLoadout | deleteLoadoutByName | Removes a named loadout, saves remaining list and refreshes UI |
| LoadoutFolders.moveFolder | swapLoadoutsInFolder | Swaps two loadout list entries, not the folder keys |

The public reference witness pins four declaring-owner SHA-256 values and a complete five-symbol source-wide reference census. The lexical tool skips Java comments, string literals and character literals, refuses changed input or identifiers, and verifies each changed file reverses exactly to R363. All 1,277 R363 source bytes are recoverable by inverse. Names are inferred, not certified original-author text.

## Private full build and independent replay

- OpenJDK 21.0.12.1, javac --release 11 -proc:none -g:none -encoding UTF-8.
- Full private compilation: **1,277 sources -> 1,386 classfiles**, exit 0.
- Candidate JAR SHA-256: **c6e958ac0be2ac4c0a90079c8555c0f999f311021e38a22fe0f1309fb630762a**.
- Independent clean extraction and rebuild reproduced identical SHA-256.
- Private R364 source archive SHA-256: **b3f3073f23b49405fa591adff8e7e9ee177397eab1df24b76bb36427e5607bcc**.
- Local synthetic test suite: **19/19 passed**. Hosted CI results must be checked independently.

The private Java sources and two binary dependencies are distributed separately to the owner, not pushed to this PUBLIC repository.

## Serializer concerns — no behavior changes

The candidate LoadoutSerializer uses DataInputStream.read(byte[]) for length-prefixed strings rather than readFully, allowing possible short reads; allocates from stored lengths without size limits; mixes platform-default length calculations with UTF-8 encoded writes; and uses EOF/error termination rather than an explicit record count.

These are static observations in reconstructed source, **not proven vulnerabilities or confirmed behavior of the untouched original v309 binary**. Do not patch the on-disk format until separately tested with compatibility and corrupt-file fixtures. R364 changes NO serializer statements or runtime behavior.

## Release gate

This source-built JAR is a readability candidate only; no original binary parity, reflection safety, live GUI, login, reconnect or inventory recovery are established. Source-M1 publication gate stays CLOSED. Keep DRAFT/UNMERGED. Production v312/updater, original v309 JAR, caches, credentials and game servers remain untouched.
