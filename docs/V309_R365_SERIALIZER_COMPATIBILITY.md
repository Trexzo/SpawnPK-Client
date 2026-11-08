# R365 — v309 loadout serialization compatibility (private candidate)

**Correct repository:** `Trexzo/SpawnPK-Client`. **Base:** R364 PR #1157. This R365 candidate changes one owner-private recovered Java source, `rs/gui/loadouts/io/LoadoutSerializer.java`, among **1,277 total Java files**. The private sources and dependency JARs are not uploaded to the public repository.

## Reproduced R364 defects

- A complete input ending cleanly between serialized records raises `EOFException` rather than returning normally. The caller catches EOF; this is not proof of a user-facing crash.
- A synthetic stream returning only one byte per `read(byte[])` can corrupt the decoded loadout name. The original method incorrectly assumes a single `read` always fills its buffer.
- Allocations use unbounded stored prefix lengths. The writer calculates names using the default charset's byte length while writing UTF-8 bytes.

## R365 private Java repair

- Use `readFully` for name/tag bytes; cap encoded names at **4,096 bytes** and tags at **256 bytes**.
- Treat EOF before the next record as clean completion, but reject partial four-byte headers and incomplete data.
- Match UTF-8 prefix lengths to bytes written. Decode v5 strings as UTF-8 while retaining legacy v1–v4 default-charset decoding.
- Preserve the **v5 field sequence and record structure**, not necessarily identical historical non-ASCII output across all default charsets.
- Leave `LoadoutStore` and all live user/cache files untouched. Its existing EOF exception recovery semantics still require assessment.

## Private verification

Real R364/R365 source ZIP hashes and changed owner's SHA-256 are pinned in `research/v309-source-recovery/r365-serializer-compatibility-witness.json`. **Exactly one of 1,277 Java source files changed**, confirmed by reading both private archives.

R365: **1,277 files compiled → 1,386 class files**, JDK21 `javac --release 11`. **Three independent clean builds, including fresh kit extraction**, produced JAR SHA-256 `f1a31f6dbfbb07d7b21115e45fee243b191560ae02eded2f441031ac6fb9eee1`. Actual private source-backed Java fixtures passed **30 assertions under UTF-8 and 30 under ISO-8859-1**, covering version 1–5 fixtures, normal records, truncated headers, invalid sizes, multi-record streams, non-ASCII names, and one-byte short reads.

Public CI is **synthetic source archive verification only**. It never compiles private Java or runs the original game. Private source binaries, login, live reconnection, and original-v309 binary parity were **NOT TESTED**.

**Release gate CLOSED. Draft and unmerged.** v312, updater, original client JAR, and caches remain unchanged.
