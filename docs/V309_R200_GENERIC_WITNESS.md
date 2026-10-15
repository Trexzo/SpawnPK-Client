# R200 synthetic Java 11 typed-collection witness

`javac --release 11` and `java` pass on a standalone synthetic deserializer returning a `List<Marker>`; verified empty and populated collection branches. Unchecked-cast warnings remain, as expected: a generic decoder's actual runtime element type is **not** proven by the cast.

This fixture is deliberately unrelated to original SpawnPK Java. It verifies the candidate source expression is legal Java 11 and returns the intended generic collection in the synthetic scenario, not authentic original-v309 semantics.

The private complete-source compiler still reports **2,001 errors** on a dependency-free build after the R200 candidate change. External library absence remains unresolved.
