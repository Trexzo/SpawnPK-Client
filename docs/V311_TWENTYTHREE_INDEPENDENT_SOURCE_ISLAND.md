# v311 — 23 original Java classes independently compiled in one source island

**Evidence date:** 2026-10-21. Private local original-client and source-to-bytecode experiment; GitHub contains no original client binary, recovered proprietary Java source, private classfiles, credentials or cache.

## Original authority and method

Exact user-supplied original `client(20261021-111920).jar` SHA-256:
`5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.

The previous eleven privately recovered Java sources, compiled in one source island using the reviewed **compile-only** `rs/t.class` alias, were joined by twelve newly reconstructed JDK-only original-v311 Java classes. All **23 source files compile TOGETHER**, with `javac --release 9 -proc:none -g:none -encoding UTF-8`, an explicitly empty game binary classpath and empty external sourcepath. The temporary alias remains `rs/t.class -> rs/RecoveredNodeV311.class` in a disposable source copy; the canonical owner-private sources and original client JAR are untouched.

The original/rebuilt `javap -c -p -s` declarations, ordered instruction byte offsets, branch targets, opcodes and resolved symbolic operands were compared, canonicalizing **only numeric constant-pool reference indexes**. The previously verified `rs/t` compile alias generated the same compiled class SHA-256 as the original 11-class isolated build, so the separately verified actual inverse-JVM-name classfile restoration applies unchanged. Both original `rs/g/e` exception handlers remain matched.

## Twelve additional actual original-v311 classes

| Original class | Exact original class SHA-256 | Independently compiled class SHA-256 | Matching original JVM instructions |
|---|---|---|---:|
| `rs/d/s.class` | `89d727b894bc6971126e35faa79479c70b587d2485b2db1c42515b63fe23fa8c` | `641cb5ea48500bc728b2fe1c43b6d7731036e0769a3764d049af661703ffdeb1` | 9/9 |
| `rs/q/a/a.class` | `ca10c12e7db08addc64ef78c4f2d3c492bce344c88e9569d9701cf4238d21199` | `cc5ba10f8a17c9c7f08c857c4c9f46576076a35c1cb28054f99f2161af6ea2d9` | 21/21 |
| `rs/w/c.class` | `e624774065cb0715a1fccbeac075880644727e877b1edad2c410cb8334c69b75` | `8bb0084e9c781ace8cd1ea95dda987c5d1ce46c3e29f09eb439c56d80749bb06` | 21/21 |
| `rs/l/e/l.class` | `d46e7d533bd95e42ed82d1428014c07e96e5945566e683fa88fa626b5bb6fd19` | `3baeb72ededc1dda69963ff86b9bd550b79161ce5a3b8141b1624c8469b89c51` | 12/12 |
| `rs/Q.class` | `bbab3088f0408c65c55565d78d26875e433aa7aae1674990b039170dee95ff94` | `ce8062ee0dbe944851e738a36cbef7789e0f0a888014956b847d881174ab4133` | 3/3 |
| `rs/k/n.class` | `ed7388e0f0095e24548d0f97afb4038d9eb1bb73f1284b86450a8a54ee2a3555` | `c8dc9253f15b0f323a624dbf3803f2737331599d5a717e94192f3fcc700504a7` | 4/4 |
| `rs/g/b.class` | `8f08722848eaacf0680835e7a8c17fbee7c4409f5cd6f3fd624d245b17fad365` | `695f11ab800ad25e94cec1a3f89b52203c502e3efddfa631fb80a83396df30cd` | 3/3 |
| `rs/cache/f.class` | `9bbad7a34de965e5915435359d9964f40055e28d60642392759365a3f0d35748` | `7f3e45667eb573e736ae9c3dc2cfd21af790493b17528e1f3e5a5704099dbc62` | 4/4 |
| `rs/plugins/b/v.class` | `736c8256c73e1fe4045a17ccaaa3f86ec8ff319811b90b2c27810024f8702242` | `a33b296004c9a67c54914bb7a3b6041f49ff9b9bf7f90b47364905fa6423a0c7` | 2/2 |
| `rs/d/x.class` | `4bdd4c2164bdd8d770762dd3cc0f5d526e008b0e0b457aedec62aa4bcf3a1731` | `14ae1d117d48dc506f38da2365e417ac4c284417a8189725aa0eea9f8bd4e66f` | 26/26 |
| `rs/s.class` | `b2ae293081bdc71b1ac2dd95f5cbd5c52d3e4dddecc51cd490fa4ba9590d0f37` | `a57bbb5b65de4261a73f49aebcbc2088035ca8cbd99e21fdf2aff3432b9cfc80` | 15/15 |
| `rs/d/l.class` | `51a5314643149ccfa23f7752fde440c41eafad96ee4768702824c26e9d6cfe5e` | `690d7e1ce2dcb7541a1e7191c6690b88215407b4c19d75b25ed0804f266df551` | 3/3 |
| **Additional twelve** | | | **123/123** |

**Current measured source island:** **23/23 compiled Java classes**, **382/382** original ordered JVM instructions and declarations matching (prior 11: 259/259; additional 12: 123/123). Private aggregate compiled-class pathname and exact content SHA manifest: `bdffb2435b890f3944ba7d5c6b719587601c81fdf8c7bc913d0b408bd6385271`. This is an output witness, not an original-classfile-byte-equality hash.

## Offline original-versus-rebuilt behavior checks

All **12/12 new isolated Java reflection comparisons passed** against separately loaded original and source-rebuilt classes (same JDK, no launcher/server): byte-array holder initialization; three-int and int/int/long getters; fixed initial dimensions; zeroed public fields; exception message; abstract class and method signatures; no-op cache method; Java interface default method; boolean predicates for negative, expected and unexpected values; string/int getter; and empty class construction.

These are selected behavior probes, **not exhaustive state-space or gameplay parity**. Two of the cases check class shape/reflection rather than independently running application behavior, so do not treat the 12/12 figure as broad runtime certification.

## Namespace and verification gates

One exploratory build included both `rs/w.class` and `rs/w/c.class`; javac correctly rejected the **second real class/package shadow** (`rs.w` type vs `rs.w` package). The conflicting `rs/w.class` was **excluded from this independent island**, and the replacement `rs/d/l.class` independently compiled and matched. No classes are silently excluded by production tooling: the bounded public verifier checks the exact selected names and requires class outputs to equal that selection.

The public `standalone_source_parity` verifier now accepts up to **64 explicitly SHA-pinned classes**, enough for this 23-source group without offering a blanket unverified 1,184-class recovery. A new synthetic Java9 CI regression constructs 23 unrelated JDK-only classes, verifies the entire batch with the empty original-game classpath, and refuses unbounded selections of 65. This hosted regression does **not** contain the real proprietary Java or original JAR.

The recovered game binary bytes, private Java sources and private compiled classes remain off GitHub. Remaining unproven: exact original classfile attributes (e.g. StackMapTable and annotations), complete original source, JVM-wide class/package remap, original v309/v310 → v311 member lineage, live gameplay and GUI behavior.

**Next step:** extend rigorously verified source islands with more original-v311 JDK-only and dependency-closed classes, then move into real dependency resolution and reviewed collision legalization for the complete client.
