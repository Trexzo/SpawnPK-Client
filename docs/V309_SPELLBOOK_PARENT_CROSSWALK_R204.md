# R204 — pinned v309 spellbook parent ↔ decompiled Class179 crosswalk

This is an evidence-collection gate for the original client source, **not** a claim that the complete `rs/n/c/ap.java` source has been reconstructed.

The exact original v309 JAR SHA256 is `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Its original `rs/n/c/ap.class` SHA256 is **`b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4`** (16,015 bytes). The nested three-value enum `rs/n/c/ap$a.class` is separately pinned to `884186742e7d92489d6634e8cb6d0012ee5e8ba71bcc272c339bed4a8a9ee7df`.

A real `javap -p -s -c` inspection of the pinned original JAR confirms class `rs.n.c.ap extends rs.n.c` and state fields `c:int`, `d:boolean`, `e:boolean`, `f:List<rs/n/c/ap$a>`. The original `h():void` method toggles `d`, invokes `j()`, `i()`, then `rs/f/a.d()`. The decompiled donor `rs/interfaces/widgets/Class179.java` has a `method1966()` matching this sequence at source level: toggle `field3646`, invoke `method236()` and `method3153()`, then `Configuration.saveSettings()`. The original `i():void` relayouts widget 1151 and invokes `java/util/Arrays.copyOf` for widget 12424 when disabled; the donor `method3153()` implements corresponding operations. These are concrete **supported crosswalk candidates**, not independently proved name maps.

The third strong overlap is spell-category filtering: the donor uses `Class176` (three decompiled enum values), `field3648:List`, `field3647:boolean`, and skill level 6; the original holds a list of the original three-value enum and includes the spellbook filtering state. The R203 original Java spellbook enum is already separately semantically recovered, but its generated alias fields are not original classfile identity.

The new verifier takes the pinned original JAR **and the actual private recovered-source tree ZIP**; it checks original owner/classfile hashes, JVM class metadata, required state field descriptors, original method descriptors and symbolic reference owners, then donor source identifiers and characteristic call sites. Its output explicitly marks exact member mapping and complete parent source reconstruction as **false**. Hosted synthetic tests exercise SHA refusal, not original-binary acceptance.

## Still unverified

- The complete original `rs/n/c/ap.java` source, superclass `rs/n/c`, and original nested `rs/n/c/ap$b`, `rs/n/c/ap$c` implementation sources.
- Exact one-to-one crosswalk for *every* field/method; class hierarchy and Java build must be checked rather than inferred from naming.
- Full private source-only compilation, original-runtime validation, StackMapTable equivalence, and redistribution rights.

**Next:** recover small original parent method bodies (e.g. `h()`, `i()`, `j()`, and `m(int)`) with complete decoded JVM code comparisons to the fixed original SHA. Only then consider a private original-named `rs/n/c/ap.java` candidate and a whole-source Javac diagnostic delta. Existing source tree count and diagnostics remain last measured at 1,295 and 2,358; no new source owner was added in R204.