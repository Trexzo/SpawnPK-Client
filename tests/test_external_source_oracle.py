from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.external_source_oracle import (
    ExternalSourceOracleError,
    build_external_source_oracle,
    index_class_directory,
)
from spk_recovery.indexer import sha256_file



def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout.strip()


def _init_git_repo(repo: Path) -> str:
    repo.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "init", str(repo)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    _run_git(repo, "config", "user.email", "oracle@example.invalid")
    _run_git(repo, "config", "user.name", "Oracle Test")
    (repo / "REVISION.txt").write_text("fixture\n", encoding="utf-8")
    _run_git(repo, "add", "REVISION.txt")
    _run_git(repo, "commit", "-m", "fixture")
    return _run_git(repo, "rev-parse", "HEAD")

def _compile(
    *,
    source_root: Path,
    class_root: Path,
    package: str,
    class_name: str,
    body: str,
) -> Path:
    src_dir = source_root / package.replace(".", "/")
    src_dir.mkdir(parents=True, exist_ok=True)
    source = src_dir / f"{class_name}.java"
    source.write_text(
        f"package {package}; public class {class_name} {{ {body} }}\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "javac",
            "-g:none",
            "-d",
            str(class_root),
            str(source),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return source


def _jar_classes(class_root: Path, jar: Path) -> None:
    with zipfile.ZipFile(jar, "w") as zf:
        for class_file in sorted(
            class_root.rglob("*.class")
        ):
            zf.write(
                class_file,
                class_file.relative_to(
                    class_root
                ).as_posix(),
            )


class ExternalSourceOracleTests(unittest.TestCase):
    def test_indexes_directory_deterministically(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            classes = root / "classes"
            classes.mkdir()
            _compile(
                source_root=root / "src",
                class_root=classes,
                package="rs.pretty",
                class_name="ReadableThing",
                body=(
                    'private int value = 7; '
                    'public String label() { return "SpawnPK"; }'
                ),
            )

            first = index_class_directory(classes)
            second = index_class_directory(classes)
            self.assertEqual(
                first["sha256"],
                second["sha256"],
            )
            self.assertEqual(
                first["summary"]["rs_class_count"],
                1,
            )
            self.assertIn(
                "rs/pretty/ReadableThing.class",
                first["classes"],
            )

    def test_structural_match_stays_research_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            external_repo = root / "external-repo"
            external_revision = _init_git_repo(external_repo)
            external_classes = external_repo / "build" / "classes"
            exact_classes = root / "exact"
            external_classes.mkdir(parents=True)
            exact_classes.mkdir()

            body = (
                'private int value = 7; '
                'public String label() { return "SpawnPK"; }'
            )
            _compile(
                source_root=root / "external-src",
                class_root=external_classes,
                package="rs.pretty",
                class_name="ReadableThing",
                body=body,
            )
            _compile(
                source_root=root / "exact-src",
                class_root=exact_classes,
                package="rs.x",
                class_name="a",
                body=body,
            )

            jar = root / "exact.jar"
            _jar_classes(exact_classes, jar)
            exact_sha = sha256_file(jar)

            report = build_external_source_oracle(
                external_repo=external_repo,
                external_classes=external_classes,
                external_revision=external_revision,
                exact_v308_jar=jar,
                expected_v308_sha256=exact_sha,
            )

            self.assertTrue(report["research_only"])
            self.assertFalse(report["source_authority"])
            self.assertFalse(report["semantic_authority"])
            self.assertFalse(
                report["source_mutation_allowed"]
            )
            self.assertEqual(
                report["summary"]["matched"],
                1,
            )
            candidate = report["candidates"][0]
            self.assertEqual(
                candidate["external_simple_name"],
                "ReadableThing",
            )
            self.assertEqual(
                candidate["exact_v308_entry"],
                "rs/x/a.class",
            )
            self.assertEqual(
                candidate["evidence_tier"],
                "strong",
            )
            self.assertTrue(
                candidate["research_name_candidate"]
            )
            self.assertFalse(
                candidate["semantic_name_accepted"]
            )

    def test_rejects_revision_and_v308_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            external_repo = root / "external-repo"
            external_revision = _init_git_repo(external_repo)
            external_classes = external_repo / "build" / "classes"
            exact_classes = root / "exact"
            external_classes.mkdir(parents=True)
            exact_classes.mkdir()
            _compile(
                source_root=root / "external-src",
                class_root=external_classes,
                package="rs.pretty",
                class_name="ReadableThing",
                body="public int value() { return 7; }",
            )
            _compile(
                source_root=root / "exact-src",
                class_root=exact_classes,
                package="rs.x",
                class_name="a",
                body="public int value() { return 7; }",
            )
            jar = root / "exact.jar"
            _jar_classes(exact_classes, jar)

            with self.assertRaisesRegex(
                ExternalSourceOracleError,
                "40-hex commit",
            ):
                build_external_source_oracle(
                    external_repo=external_repo,
                    external_classes=external_classes,
                    external_revision="main",
                    exact_v308_jar=jar,
                    expected_v308_sha256=sha256_file(
                        jar
                    ),
                )

            with self.assertRaisesRegex(
                ExternalSourceOracleError,
                "external revision drift",
            ):
                build_external_source_oracle(
                    external_repo=external_repo,
                    external_classes=external_classes,
                    external_revision="b" * 40,
                    exact_v308_jar=jar,
                    expected_v308_sha256=sha256_file(
                        jar
                    ),
                )

            with self.assertRaisesRegex(
                ExternalSourceOracleError,
                "SHA-256 mismatch",
            ):
                build_external_source_oracle(
                    external_repo=external_repo,
                    external_classes=external_classes,
                    external_revision=external_revision,
                    exact_v308_jar=jar,
                    expected_v308_sha256="0" * 64,
                )

    def test_rejects_path_internal_name_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            compiled = root / "compiled"
            compiled.mkdir()
            _compile(
                source_root=root / "src",
                class_root=compiled,
                package="rs.pretty",
                class_name="ReadableThing",
                body="public int value() { return 7; }",
            )
            original = (
                compiled
                / "rs"
                / "pretty"
                / "ReadableThing.class"
            )
            wrong = compiled / "rs" / "wrong.class"
            wrong.parent.mkdir(parents=True, exist_ok=True)
            original.replace(wrong)

            with self.assertRaisesRegex(
                ExternalSourceOracleError,
                "path/internal-name mismatch",
            ):
                index_class_directory(compiled)


if __name__ == "__main__":
    unittest.main()
