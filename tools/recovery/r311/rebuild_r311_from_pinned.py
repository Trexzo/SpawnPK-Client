#!/usr/bin/env python3
"""R311 private full recovered-source build from exact pinned R278/R265 inputs.

Public recipe only: the owner keeps original-derived Java, dependency JARs,
cache and game binaries private. Compilation does not launch the client.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, re, shutil, tempfile
from pathlib import Path

PREVIOUS_GIT_BLOB = "186cbc76f4e08bc5133f3899038f1e56ef4166b8"
OLD_SCENE = "63b3bc9d7b01f5337ca859616196f08af635f28dbf119caa11f55dadec43d4bc"
NEW_SCENE = "c38fb283d7b2a6d21c0df6f0755c0608e39bfa9a157d56ef1e2ccd53e4109e94"
NEW_JAR = "b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def patch_scene(data: bytes) -> bytes:
    if sha(data) != OLD_SCENE:
        raise ValueError("R311_SCENE_PREIMAGE_SHA_MISMATCH")
    source = data.decode("utf8")
    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError("R311_ANCHOR_DRIFT")
        source = source.replace(old, new)
    loop = re.compile(r"for \(int (var\d+) = 0; \1 < (var\d+)\.field5057; \1\+\+\)")
    matches = list(loop.finditer(source))
    expected = [("var6","var5"),("var5","var4"),("var5","var4"),
                ("var6","var5"),("var12","var11"),("var5","var4"),
                ("var7","var4"),("var5","var4"),("var5","var4"),
                ("var13","var11"),("var18","var15"),("var11","var27"),
                ("var37","var3")]
    if [(m.group(1),m.group(2)) for m in matches] != expected:
        raise ValueError("R311_LOOP_TOPOLOGY_DRIFT")
    begin = source.index("   private void method3235(")
    end = source.index("   public void method3478(", begin)
    mutated = [m for m in matches if begin < m.start() < end]
    if len(mutated) != 2:
        raise ValueError("R311_MUTATION_LOOP_DRIFT")
    for m in reversed(matches):
        if m in mutated:
            continue
        variable, owner = m.group(1), m.group(2)
        source = source[:m.start()] + (
            f"for (int {variable} = 0; {variable} < boundedSceneObjectCount({owner}); {variable}++)"
        ) + source[m.end():]
    replace("if (var17 != null && var17.field5057 >= 5) {",
            "if (var17 != null && (var17.field5057 < 0 || var17.field5057 >= var17.field5058.length)) {")
    replace("if (var16 != null && var16.field5057 >= 5) {",
            "if (var16 != null && (var16.field5057 < 0 || var16.field5057 >= var16.field5058.length)) {")
    replace("""            Tile var4 = this.tiles[plane][var2][var3];
            if (var4 != null) {
               for (int var5 = 0; var5 < var4.field5057; var5++) {""",
            """            Tile var4 = this.tiles[plane][var2][var3];
            if (var4 != null && validSceneObjectCount(var4)) {
               for (int var5 = 0; var5 < var4.field5057; var5++) {""")
    replace("if (var3.field5058[var37].field1536 != field5671 &&",
            "if (var3.field5058[var37] != null && var3.field5058[var37].field1536 != field5671 &&")
    replace("int var30 = var3.field5057;", "int var30 = boundedSceneObjectCount(var3);")
    replace("""                  graphics_ var52 = var3.field5058[var47];
                  if (var52.field1536 != field5671) {""",
            """                  graphics_ var52 = var3.field5058[var47];
                  if (var52 != null && var52.field1536 != field5671) {""")
    replace("""   private boolean hasTrackedObjectCapacity() {""",
            """   // Corrupted/partially populated tiles can survive asynchronous region transitions.
   // Reads inspect only physical slots; mutations require valid authoritative counts.
   private static int boundedSceneObjectCount(Tile tile) {
      return tile == null ? 0 : Math.max(0, Math.min(tile.field5057, tile.field5058.length));
   }

   private static boolean validSceneObjectCount(Tile tile) {
      return tile != null && tile.field5057 >= 0 && tile.field5057 <= tile.field5058.length;
   }

   private boolean hasTrackedObjectCapacity() {""")
    result = source.encode("utf8")
    if sha(result) != NEW_SCENE:
        raise ValueError("R311_SCENE_POSTIMAGE_SHA_MISMATCH")
    return result

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r278", type=Path, required=True)
    parser.add_argument("--r265", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--javac", default="javac")
    args = parser.parse_args(argv)
    output = args.output.absolute()
    if output.exists() or output.is_symlink() or not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError("R311_OUTPUT_MUST_BE_NEW_IN_SAFE_FOLDER")
    prior = Path(__file__).resolve().parents[1] / "r310" / "rebuild_r310_from_pinned.py"
    if not prior.is_file() or prior.is_symlink():
        raise ValueError("R311_PRIOR_BUILDER_MISSING")
    raw = prior.read_bytes()
    git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if git_blob != PREVIOUS_GIT_BLOB:
        raise ValueError("R311_PRIOR_BUILDER_HASH_MISMATCH")
    spec = importlib.util.spec_from_file_location("r311_owner_prior", prior)
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    old_patch = previous.patch_scene
    previous.patch_scene = lambda data: patch_scene(old_patch(data))
    previous.PIN_R310_JAR = NEW_JAR
    with tempfile.TemporaryDirectory(prefix="r311-full-source-", dir=output.parent) as temp:
        stage = Path(temp) / "stage"
        previous.main(["--r278", str(args.r278), "--r265", str(args.r265),
                       "--output", str(stage), "--javac", args.javac])
        jar = stage / "R310_SOURCE_BUILT_CLASS_ONLY.jar"
        if sha(jar.read_bytes()) != NEW_JAR:
            raise ValueError("R311_BINARY_SHA_MISMATCH")
        jar.rename(stage / "R311_SOURCE_BUILT_CLASS_ONLY.jar")
        (stage / "R310_BUILD_MANIFEST.json").unlink()
        (stage / "R311_BUILD_MANIFEST.json").write_text(json.dumps({
            "milestone":"R311", "java_source_files":1277, "compiled_classes":1386,
            "scene_source_sha256":NEW_SCENE, "jar_sha256":NEW_JAR,
            "changed_classfiles":["rs/Scene.class"],
            "native_windows_gpu":"NOT_TESTED", "authenticated_gameplay":"NOT_TESTED"
        }, indent=2, sort_keys=True) + "\n")
        shutil.move(str(stage), str(output))
    print("R311_PRIVATE_FULL_SOURCE_REPLAY_PASS java=1277 classes=1386 jar="+NEW_JAR)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
