import hashlib
import struct
import tempfile
from pathlib import Path
import unittest

from spk_recovery.external_corpus_probe import (
    EXACT_V308_SHA256,
    ExternalCorpusProbeError,
    build_external_corpus_probe,
    index_class_directory,
)


def _class(
    fp: str,
    *,
    internal_name: str,
    strings=None,
    numbers=None,
    fields=None,
    methods=None,
    access=1,
    major=55,
):
    fields = fields or []
    methods = methods or []
    return {
        "internal_name": internal_name,
        "major": major,
        "minor": 0,
        "access": access,
        "super_name": "java/lang/Object",
        "interfaces": [],
        "field_count": len(fields),
        "method_count": len(methods),
        "fields": fields,
        "methods": methods,
        "attributes": [],
        "inner_outer_name": None,
        "inner_simple_name": None,
        "enclosing_class_name": None,
        "literal_strings": strings or [],
        "numeric_constants": numbers or [],
        "structural_sha256": fp,
    }


def _index(
    sha: str,
    classes: dict,
    *,
    parse_errors=None,
):
    entries = {
        path: {
            "sha256": hashlib.sha256(
                path.encode("utf-8")
            ).hexdigest(),
            "size": 100,
        }
        for path in classes
    }
    rs_count = sum(
        1
        for path in classes
        if path.startswith("rs/")
    )
    parse_errors = parse_errors or {}
    return {
        "sha256": sha,
        "entries": entries,
        "classes": classes,
        "summary": {
            "class_count": len(classes),
            "rs_class_count": rs_count,
            "class_parse_error_count": len(
                parse_errors
            ),
            "class_parse_errors": parse_errors,
        },
    }


def _u1(value: int) -> bytes:
    return struct.pack(">B", value)


def _u2(value: int) -> bytes:
    return struct.pack(">H", value)


def _u4(value: int) -> bytes:
    return struct.pack(">I", value)


def _utf8(value: str) -> bytes:
    raw = value.encode("utf-8")
    return _u1(1) + _u2(len(raw)) + raw


def _cp_class(index: int) -> bytes:
    return _u1(7) + _u2(index)


def _minimal_class_bytes(
    internal_name: str,
) -> bytes:
    cp = [
        _utf8(internal_name),
        _cp_class(1),
        _utf8("java/lang/Object"),
        _cp_class(3),
    ]
    out = bytearray()
    out += _u4(0xCAFEBABE)
    out += _u2(0)
    out += _u2(55)
    out += _u2(len(cp) + 1)
    for entry in cp:
        out += entry
    out += _u2(0x0021)
    out += _u2(2)
    out += _u2(4)
    out += _u2(0)
    out += _u2(0)
    out += _u2(0)
    out += _u2(0)
    return bytes(out)


class ExternalCorpusProbeTests(unittest.TestCase):
    def test_structural_match_is_candidate_only(self):
        external_sha = "1" * 64
        external = _index(
            external_sha,
            {
                "rs/model/Player.class": _class(
                    "same-fingerprint",
                    internal_name="rs/model/Player",
                    strings=["Combat level"],
                    numbers=[185],
                )
            },
        )
        exact = _index(
            EXACT_V308_SHA256,
            {
                "rs/a/b.class": _class(
                    "same-fingerprint",
                    internal_name="rs/a/b",
                    strings=["Combat level"],
                    numbers=[185],
                )
            },
        )

        report = build_external_corpus_probe(
            external_index=external,
            exact_index=exact,
            external_revision="a" * 40,
        )

        self.assertTrue(
            report["policy"]["research_only"]
        )
        self.assertFalse(
            report["policy"]["promotes_names"]
        )
        self.assertFalse(
            report["policy"]["copies_external_source"]
        )
        self.assertEqual(
            report["summary"]["structural_matches"],
            1,
        )
        self.assertEqual(
            report["summary"][
                "descriptive_name_candidates"
            ],
            1,
        )
        row = report["candidates"][0]
        self.assertEqual(
            row["external_readable_name"],
            "Player",
        )
        self.assertEqual(
            row["exact_v308_path"],
            "rs/a/b.class",
        )
        self.assertTrue(row["candidate_only"])
        self.assertFalse(row["promoted"])

    def test_exact_v308_pin_is_fail_closed(self):
        external = _index(
            "1" * 64,
            {
                "rs/A.class": _class(
                    "fp",
                    internal_name="rs/A",
                )
            },
        )
        exact = _index(
            "2" * 64,
            {
                "rs/a.class": _class(
                    "fp",
                    internal_name="rs/a",
                )
            },
        )
        with self.assertRaisesRegex(
            ExternalCorpusProbeError,
            "pinned v308 authority",
        ):
            build_external_corpus_probe(
                external_index=external,
                exact_index=exact,
                external_revision="a" * 40,
            )

    def test_external_parse_errors_are_refused(self):
        external = _index(
            "1" * 64,
            {
                "rs/A.class": _class(
                    "fp",
                    internal_name="rs/A",
                )
            },
            parse_errors={
                "rs/B.class": "bad class"
            },
        )
        exact = _index(
            EXACT_V308_SHA256,
            {
                "rs/a.class": _class(
                    "fp",
                    internal_name="rs/a",
                )
            },
        )
        with self.assertRaisesRegex(
            ExternalCorpusProbeError,
            "external index contains class parse errors",
        ):
            build_external_corpus_probe(
                external_index=external,
                exact_index=exact,
                external_revision="a" * 40,
            )

    def test_revision_must_be_exact_commit(self):
        external = _index(
            "1" * 64,
            {
                "rs/A.class": _class(
                    "fp",
                    internal_name="rs/A",
                )
            },
        )
        exact = _index(
            EXACT_V308_SHA256,
            {
                "rs/a.class": _class(
                    "fp",
                    internal_name="rs/a",
                )
            },
        )
        with self.assertRaisesRegex(
            ExternalCorpusProbeError,
            "40-hex",
        ):
            build_external_corpus_probe(
                external_index=external,
                exact_index=exact,
                external_revision="main",
            )

    def test_directory_index_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "rs" / "Example.class"
            target.parent.mkdir(parents=True)
            target.write_bytes(
                _minimal_class_bytes("rs/Example")
            )
            first = index_class_directory(root)
            second = index_class_directory(root)

        self.assertEqual(
            first["sha256"],
            second["sha256"],
        )
        self.assertEqual(
            first["summary"]["class_count"],
            1,
        )
        self.assertEqual(
            first["summary"]["rs_class_count"],
            1,
        )
        self.assertEqual(
            first["summary"][
                "class_parse_error_count"
            ],
            0,
        )
        self.assertEqual(
            first["classes"][
                "rs/Example.class"
            ]["internal_name"],
            "rs/Example",
        )


if __name__ == "__main__":
    unittest.main()
