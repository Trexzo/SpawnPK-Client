# R186 — original v309 Signlink/bridge 21 of 24 Java methods (469 JVM instructions)

Client-only original JVM method-body recovery, stacked on [R185 #1078](https://github.com/Trexzo/SpawnPK-Client/pull/1078), source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). This is **NOT** original full-class acceptance.

## Original source recovery results — private pinned v309 evidence

Full original v309 client JAR SHA-256:
ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38

Original rs/v/a.class SHA-256:
d0dc35deddc8016c3fdcaf2615810efa200c042120b83bed86cad5d04b1c0ddc

R183→R184→R185 selected Java source had 16 selected methods, 356/356 original JVM instructions. Five newly reconstructed original rs/v/a.java Java9 selected methods are:

| New original method | Original JVM instructions |
| --- | ---: |
| b():String — data-directory path | 42/42 |
| f():String — cache-directory path | 42/42 |
| d():boolean — runtime/platform predicate | 7/7 |
| e():String — external identifier fallback | 17/17 |
| a(double):void — audio control | 5/5 |
| Newly restored | **113/113** |
| All selected 21 methods | **469/469** |

Locally rebuilt the private one-original-named Java file with JDK21 javac --release 9 -g:none -proc:none -implicit:none, an EMPTY original/external compiled classpath, and six separately invented **compiler-only interface declarations** for original-referenced rs/f/a, rs/k/j, rs/w/c and rs/secure/a, rs/secure/b, rs/secure/c. All 21 selected original/rebuilt instructions matched original offsets, operation codes, operands and resolved method/field comments in javap; original selected string-concat bootstrap recipes and symbolic references are checked by the repo strict comparator, which the new private-input verifier invokes separately.

Due to JVM constant-pool numbering, initial otherwise-equivalent method placement widened some ldc to ldc_w. Reordering source method declarations without changing selected behavior allows all 21 method-Code layouts to reproduce the original.

Exact private 21-method Java source ZIP SHA256:
051b9f1a50e33422e1480aba3d6db6322894e9142b0cb08fb3e4bb6f88040798

Exact private Java source text SHA256:
837111e5198c38c87248d19213b625f3986992f2ab505f1537832edb8650e1c3

The six compiler-only helper declarations ZIP SHA256:
25e8aa030b1c3f3a02a6148102a6337c16a3bc2f2b84595d825c92cd1c277448

Prior exact private source ZIP SHA256: 6-method 28ffe7d1b1e29f5d6e6466684423548d233ebdb7d498d7666aa6f6ea2c3371ad; 11-method 3872fd5e21a3049ad5bdb6a0686937fedb35c869a79772fff89918918b968907; 16-method 69c989c677d3032b3d79c5a15f56cb486dd13d9b4863b0dba6d9a0960bbafd68.

## New public GitHub verifier and CI

The R186 verifier SHA-pins the full original class, all four successive original-derived Java source ZIPs, and the exact six compiler-only helper owner declarations; it first reruns R183→R184→R185 acceptance, independently recompiles original-named Java9 candidate plus only explicitly enumerated helper declarations with an empty original/external classpath and sourcepath, checks owner/class version, exact emitted class set, 21 complete selected method-Code bodies against original resolved JVM instructions, stack and local limits and handlers, and refuses nonoriginal compiled helper output as evidence.

Hosted Ubuntu/Windows synthetic regression tests use entirely unrelated invented Java implementation, with analogous method identities and invented declaration-only helper classes. They test chained staging, changed earlier/new selected methods, altered unselected run placeholder, wrong SHA pins, missing helpers and wrong source owner. No original JAR or original-derived Java is committed to GitHub.

## Hard acceptance exclusions

Original rs/v/a has **24 JVM methods**; exactly THREE remain unverified: g():String, run():void and <clinit>():void. The expanded private class still has an unverified run() implementation and an incomplete original field/initializer ABI. Selected method bodies invoking other original classes do not certify those classes (all six helpers are fake declaration-only compiler aids, not original code). Optional JVM Exceptions attributes are not fully equivalent for some rebuilt selected methods; selected JVM Code parity must not be described as full classfile equivalence.

No full original runtime/network execution, complete class field or support-type source recovery, canonical recovered-source/v309/src overlay, whole-client compilation, javac error reduction or source redistribution authority is claimed. Keep R186 a DRAFT until dedicated hosted CI AND actual private SHA-pinned source verifier replay pass.

Next: recover g(), run() and <clinit> against all original instructions. Replace dependency stubs with independently verified original helper class source and inspect original nested rs/v/a$a behavior, then recompile whole original class and integrate with R179 Packet/ISAAC in a single SHA-measured private source tree.
