import json
import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_DIR = ROOT / "mappings" / "candidates"
REVIEW_RE = re.compile(r"^v308\.semantic-review\.chat2\.r(\d+)\.json$")


class Chat2SemanticReviewUniquenessTests(unittest.TestCase):
    def test_no_target_coordinate_is_reintroduced_in_later_review_batch(self):
        seen = {}
        duplicates = []

        reviews = []
        for path in CANDIDATE_DIR.glob("v308.semantic-review.chat2.r*.json"):
            match = REVIEW_RE.match(path.name)
            if match:
                reviews.append((int(match.group(1)), path))

        for batch, path in sorted(reviews):
            review = json.loads(path.read_text(encoding="utf-8"))
            for proposal in review.get("proposals", []):
                source = proposal.get("source_coordinate") or {}
                key = (
                    proposal.get("target_kind"),
                    proposal.get("stable_id"),
                    source.get("owner"),
                    source.get("name"),
                    source.get("descriptor"),
                )
                previous = seen.get(key)
                if previous is not None:
                    duplicates.append(
                        {
                            "target": key,
                            "first_batch": previous["batch"],
                            "first_path": previous["path"],
                            "first_name": previous["name"],
                            "duplicate_batch": batch,
                            "duplicate_path": path.name,
                            "duplicate_name": proposal.get("proposed_name"),
                        }
                    )
                else:
                    seen[key] = {
                        "batch": batch,
                        "path": path.name,
                        "name": proposal.get("proposed_name"),
                    }

        self.assertEqual(
            duplicates,
            [],
            "Chat 2 semantic target(s) were reintroduced in later review batches: "
            + json.dumps(duplicates, sort_keys=True),
        )


if __name__ == "__main__":
    unittest.main()
