# R177: original Packet parent Java restoration

The original client Packet inherits `rs/x/e → rs/a → rs/t → Object`. Two complete original-derived Java parent sources, `rs/a.java` and `rs/t.java`, were privately rebuilt using Java 9 with no original or external classfile dependencies. Both constructors and both linked-list unlink methods match their original JVM method identifiers, access flags, local/stack limits, offsets and resolved references: **4 methods, 48 instructions**.

Original v309 JAR SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Original rs/t.class SHA256: `430c61233ef1d46a3dadbe4947a3d4d17019db2bc1d4678dc732623ea1b3274f`; rs/a.class SHA256: `7c33983b6e49dc2cd8b4b5bde2bd0550a4977c1eaa483025630b5c16105e735f`. Private two-source ZIP SHA256: `3bceb9bb9a06741c323397b3e2600ff436cacab42b3f082eac0e718e147bf218`. Private full-class proof JSON SHA256: `d94d638641ad7404b8bfdee7dfcff82c580e93af87a6740c18c77f754ce778c0`.

All prior 1,276 private original client Java candidate files were copied unchanged; the two complete parents were added into a new PRIVATE 1,278-file candidate ZIP SHA256 `dd68b18a4e60e7d9b2431811a1531f4e33bfa75ac1adb9a4f07100a64e99d6da`. The partial Packet source remains excluded.

A controlled JDK-only Java 9 compile of all sources, with the same flags and no external/project binary classpath, reports **2,339 errors before and 2,339 after** the new parents. No full-client compilation or error reduction is claimed. Public GitHub contains only the verifier, synthetic tests and sanitized evidence, not original game Java or classfiles. Complete original Packet source, original source distribution rights and whole-client compilation remain outstanding.
