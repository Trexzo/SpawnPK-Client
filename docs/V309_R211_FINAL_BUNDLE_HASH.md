# R211 final private handoff

The complete Java 11 source build has been verified locally. A final private ZIP additionally contains an optional local-only resource overlay script; it requires the original JAR SHA-256 match before creating a local resource-only archive, and does not include original game classes.

Final private bundle SHA-256: `7130e83a3dcb1dc78b8d9b876786313758e94b7e829b48da467445c5b1834dc1`.

Full Java build: 1,275 sources, 1,376 classfiles, zero errors. Nine offline tests passed; one UI-layout check failed. Matrix bridge matched 1,000 original v309 reference inputs. Launcher with actual graphical resources and full original bytecode parity remain unverified.
