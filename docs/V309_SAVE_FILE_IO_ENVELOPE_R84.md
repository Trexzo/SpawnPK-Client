# R84 — original v309 364-op settings-save file I/O envelope

After R82–R83 classified the 47 original BufferedWriter.write(String) sites, R84 reconstructs the exact remaining outer file-handling boundaries in the SHA-256-pinned original save method.

The method's first 20 JVM instructions open a File using one original field-dependent StringConcatFactory path, conditionally call createNewFile(), and construct BufferedWriter(FileWriter(File)). Its final 28 instructions close the writer, construct temporary/destination Paths, copy with StandardCopyOption.REPLACE_EXISTING, delete the temporary file, skip the original catch on success, and printStackTrace on an Exception. The one original Exception handler covers start offset 0 through 920 with handler offset 923.

This research-only tool requires the R83 full 47-write site-classification proof first. It verifies exact original opcode windows, constructors, method descriptors, path-field identity, original StringConcatFactory recipes, explicit branches and exception range before emitting private bounded Java source text. Original obfuscated identifiers and literal path contents are never committed or included in aggregate outputs.

Private replay:
python -m spk_recovery.properties_save_io_envelope ORIGINAL_JAR PRIVATE_OWNER.class PRIVATE_SAVE_METHOD "()V" NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_WHOLE_JAR_SHA256

It has not yet been replayed by this generic CLI against the private original, and does not itself assemble or compile the complete 364-instruction Java method. Exact file-system runtime behavior and outside helper semantics remain unverified.