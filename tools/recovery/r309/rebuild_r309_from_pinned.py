#!/usr/bin/env python3
"""R309 private full-source stability build; retains SHA-pinned R308 provenance.

Public source-safe recipe. Original client Java, owner game binaries, assets,
credentials and original private dependency jars must remain local to the owner.
No game code is executed, installed or connected to a network by this builder.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

PIN_R307_BUILDER = '176c0322183f3180bed905d9fb71f3d0e3e9ed9098b46ab182a29aa92edd4140'
PIN_R308_BUILDER = '9050dbd8e27ba76d8f7a62eab71f8b764d7379e59b4e1c5671a922e514c7c4cd'
R308_SCENE = 'baa165aacae5d9408c21235bef656ab459b41e666906991ea49ed4622d23aeae'
R309_SCENE = '245ff4d6ac3789b8e8a8c739a935e8d5904a2d6ab19c1f5f3f2041673cd7d932'
R309_JAR = '1028aa8ca1a246fdac1c806d6e2868a9bed0ccc806f641ff069c6bcc32c12e28'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def module(path: Path, expected_hash: str):
    if not path.is_file() or path.is_symlink() or sha(path.read_bytes()) != expected_hash:
        raise ValueError('R309_PUBLIC_BUILDER_SHA_MISMATCH: ' + path.name)
    spec = importlib.util.spec_from_file_location('r309_' + path.stem, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def patch_scene(prior: bytes) -> bytes:
    """Tightly scoped safety changes; requires the exact verified private R308 Scene."""
    if sha(prior) != R308_SCENE:
        raise ValueError('R309_SCENE_PREIMAGE_SHA_MISMATCH')
    text = prior.decode('utf8')

    def replace(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError('R309_ORIGINAL_METHOD_ANCHOR_DRIFT')
        text = text.replace(old, new)

    replace('''         this.method3235(var2);
         if (var2 != null) {''',
            '''         if (var2 != null) {
            this.method3235(var2);
         }
         if (var2 != null) {''')
    replace('''   private void method3235(graphics_ var1) {
      for (int var2 = var1.field1531; var2 <= var1.field1532; var2++) {
         for (int var3 = var1.field1533; var3 <= var1.field1534; var3++) {
            Tile var4 = this.tiles[var1.field1527][var2][var3];''',
            '''   private void method3235(graphics_ var1) {
      // A queued object removal may outlive the region/plane it originated from.
      // Restrict the old object's footprint to valid tiles before dereferencing it.
      if (var1 == null || var1.field1527 < 0 || var1.field1527 >= this.tiles.length) {
         return;
      }
      int plane = var1.field1527;
      int endX = Math.min(var1.field1532, this.tiles[plane].length - 1);
      for (int var2 = Math.max(0, var1.field1531); var2 <= endX; var2++) {
         int endY = Math.min(var1.field1534, this.tiles[plane][var2].length - 1);
         for (int var3 = Math.max(0, var1.field1533); var3 <= endY; var3++) {
            Tile var4 = this.tiles[plane][var2][var3];''')
    replace('''   public void method637(int[] var1, int var2, int var3, int var4, int var5) {
      int var6 = 512;
      Tile var7 = this.tiles[var3][var4][var5];''',
            '''   public void method637(int[] var1, int var2, int var3, int var4, int var5) {
      int var6 = 512;
      // A 4x4 minimap stamp touches 4 pixels across and four rows of stride 512.
      // Reject stale region coordinates and incomplete pixel buffers atomically.
      if (!this.isSceneTileInBounds(var3, var4, var5) || var1 == null
         || var2 < 0 || var2 > var1.length - (3 * var6 + 4)) {
         return;
      }
      Tile var7 = this.tiles[var3][var4][var5];''')
    result = text.encode('utf8')
    if sha(result) != R309_SCENE:
        raise ValueError('R309_SCENE_POSTIMAGE_SHA_MISMATCH')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r278', required=True, type=Path)
    parser.add_argument('--r265', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--javac', default='javac')
    args = parser.parse_args(argv)
    out = args.output.absolute()
    if out.exists() or out.is_symlink():
        raise FileExistsError('R309_REFUSE_EXISTING_OUTPUT')
    if not out.parent.is_dir() or out.parent.is_symlink():
        raise FileNotFoundError('R309_REFUSE_UNSAFE_PARENT')
    base = Path(__file__).resolve().parents[1]
    r307 = module(base / 'r307/rebuild_r307_from_pinned.py', PIN_R307_BUILDER)
    r308 = module(base / 'r308/rebuild_r308_from_pinned.py', PIN_R308_BUILDER)
    old_patch = r307.patch_scene
    r307.patch_scene = lambda data: patch_scene(r308.patch_placement_bounds(old_patch(data)))
    r307.JAR_SHA = R309_JAR
    with tempfile.TemporaryDirectory(prefix='r309-source-build-', dir=out.parent) as workspace:
        temp = Path(workspace) / 'result'
        r307.main(['--r278', str(args.r278), '--r265', str(args.r265), '--output',
                   str(temp), '--javac', args.javac])
        jar = temp / 'R307_SOURCE_BUILT_CLASS_ONLY.jar'
        if sha(jar.read_bytes()) != R309_JAR:
            raise ValueError('R309_COMPILED_JAR_SHA_MISMATCH')
        jar.rename(temp / 'R309_SOURCE_BUILT_CLASS_ONLY.jar')
        (temp / 'R307_BUILD_MANIFEST.json').unlink()
        (temp / 'R309_BUILD_MANIFEST.json').write_text(json.dumps({
            'milestone': 'R309', 'source_files': 1277, 'classfiles': 1386,
            'scene_source_sha256': R309_SCENE, 'built_jar_sha256': R309_JAR,
            'original_owner_java_in_package': False,
            'changed_compiled_classfiles': ['rs/Scene.class'],
            'native_windows_acceptance': 'NOT_TESTED',
            'authenticated_server_gameplay': 'NOT_TESTED'
        }, indent=2, sort_keys=True) + '\n')
        shutil.move(str(temp), str(out))
    print('R309_PRIVATE_FULL_TREE_BUILD_PASS sources=1277 classes=1386 jar_sha256=' + R309_JAR)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
