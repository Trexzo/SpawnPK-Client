"""Java 9 regression: recover a real dependency-connected timer registry island.

This is an unrelated synthetic JDK-only fixture, not the proprietary game
source. It exercises the same original-class dependency shape observed in
v311: abstract timer <- concrete timer <- keyed timer registry.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.source_island_frontier import (
    SourceFrontierError, discover_original_source_frontier,
)
from spk_recovery.standalone_source_parity import (
    StandaloneSourceParityError, verify_standalone_sources,
)


SOURCES = {
    "rs/fixture/BaseClock.java": """package rs.fixture;
public abstract class BaseClock {
    public abstract boolean active();
    public abstract long remaining();
}
""",
    "rs/fixture/CountingClock.java": """package rs.fixture;
public final class CountingClock extends BaseClock {
    private final long duration;
    public CountingClock(long duration) { this.duration = duration; }
    public boolean active() { return duration > 0; }
    public long remaining() { return duration; }
}
""",
    "rs/fixture/ClockRegistry.java": """package rs.fixture;
import java.util.HashMap;
import java.util.Map;
public final class ClockRegistry {
    private final Map<String,BaseClock> values = new HashMap<String,BaseClock>();
    public boolean add(String key, long duration) {
        if (values.containsKey(key)) return false;
        values.put(key, new CountingClock(duration));
        return true;
    }
    public long remaining(String key) {
        BaseClock timer = values.get(key);
        return timer == null ? 0L : timer.remaining();
    }
    public void clear() { values.clear(); }
}
""",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(shutil.which("javac") and shutil.which("javap"),
                     "Requires a JDK")
class TimerRegistrySourceIslandTests(unittest.TestCase):
    def original_fixture(self, directory: Path):
        src = directory / "source"
        for name, body in SOURCES.items():
            path = src / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        compiled = directory / "original-classfiles"
        compiled.mkdir()
        proc = subprocess.run([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-encoding", "UTF-8",
            "-classpath", str(directory / "empty-classpath"),
            "-sourcepath", str(directory / "empty-sourcepath"),
            "-d", str(compiled),
            *[str(src / name) for name in sorted(SOURCES)],
        ], capture_output=True, text=True, timeout=55)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        jar = directory / "synthetic-original.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            for path in sorted(compiled.rglob("*.class")):
                archive.writestr(
                    path.relative_to(compiled).as_posix(),
                    path.read_bytes(),
                )
        with zipfile.ZipFile(jar) as archive:
            original_hashes = {
                name: digest(archive.read(name))
                for name in archive.namelist()
            }
        self.assertEqual(len(original_hashes), 3)
        return jar, src, original_hashes

    def test_recovery_frontier_two_stages_then_three_source_parity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jar, src, original = self.original_fixture(root)
            original_sha = digest(jar.read_bytes())
            base = "rs/fixture/BaseClock.class"
            timer = "rs/fixture/CountingClock.class"
            registry = "rs/fixture/ClockRegistry.class"

            manifest = {
                "original_jar_sha256": original_sha,
                "original_class_sha256": {base: original[base]},
            }
            first = discover_original_source_frontier(jar, manifest)
            self.assertEqual(
                [x["original_class_path"] for x in first["candidates"]],
                [timer],
            )
            self.assertFalse(first["candidates"][0]["source_reconstructed"])
            self.assertEqual(
                first["candidates"][0]["direct_original_project_dependencies"],
                [base],
            )

            manifest["original_class_sha256"][timer] = original[timer]
            second = discover_original_source_frontier(jar, manifest)
            self.assertEqual(
                [x["original_class_path"] for x in second["candidates"]],
                [registry],
            )
            self.assertEqual(
                second["candidates"][0]["direct_original_project_dependencies"],
                [base, timer],
            )

            # A frontiers-only manifest must not count as a complete source
            # build. The missing timer cannot silently load from the JAR.
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "PROJECT_SOURCE_DEPENDENCY_OUTSIDE_SELECTION",
            ):
                verify_standalone_sources(
                    jar, src, root / "refused-incomplete-source-island",
                    original_sha256=original_sha,
                    class_sha256={
                        base: original[base], registry: original[registry],
                    },
                )
            self.assertFalse(
                (root / "refused-incomplete-source-island").exists()
            )

            report = verify_standalone_sources(
                jar, src, root / "accepted",
                original_sha256=original_sha,
                class_sha256=original,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 3)
            self.assertGreater(report["total_ordered_instructions"], 20)
            self.assertEqual(
                report["explicit_original_project_dependency_closure"][
                    "source_project_dependency_edges"
                ], 3,
            )
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            self.assertFalse(report["complete_v311_source_recovery"])
            self.assertTrue(all(
                r["ordered_symbolic_instruction_parity"]
                for r in report["results"]
            ))

    def test_authority_sha_fail_closed_before_candidate_output(self):
        with tempfile.TemporaryDirectory() as temp:
            jar, src, original = self.original_fixture(Path(temp))
            base = "rs/fixture/BaseClock.class"
            authority = {
                "original_jar_sha256": digest(jar.read_bytes()),
                "original_class_sha256": {base: "f" * 64},
            }
            with self.assertRaisesRegex(
                SourceFrontierError,
                "SOURCE_FRONTIER_ORIGINAL_CLASS_SHA_MISMATCH",
            ):
                discover_original_source_frontier(jar, authority)


if __name__ == "__main__":
    unittest.main(verbosity=2)
