import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "mappings" / "candidates"
REVIEW_RE = re.compile(r"^v308\.semantic-review\.chat2\.r(\d+)\.json$")


class Chat2SemanticReviewGlobalUniquenessTests(unittest.TestCase):
    def test_post_seed_class_reviews_are_globally_unique(self):
        seen_names = {}
        seen_owners = {}
        seen_stable_ids = {}
        seen_review_ids = {}

        review_paths = []
        for path in CANDIDATES.glob("v308.semantic-review.chat2.r*.json"):
            match = REVIEW_RE.match(path.name)
            if match and int(match.group(1)) >= 3:
                review_paths.append((int(match.group(1)), path))
        review_paths.sort()

        for batch, path in review_paths:
            review = json.loads(path.read_text(encoding="utf-8"))
            review_id = review["review_id"]

            self.assertNotIn(
                review_id,
                seen_review_ids,
                f"duplicate deterministic review_id {review_id}: "
                f"R{seen_review_ids.get(review_id)} and R{batch}",
            )
            seen_review_ids[review_id] = batch

            for proposal in review.get("proposals", []):
                if proposal.get("target_kind") != "class":
                    continue

                name = proposal["proposed_name"]
                owner = proposal["source_coordinate"]["owner"]
                stable_id = proposal["stable_id"]

                self.assertNotIn(
                    name,
                    seen_names,
                    f"duplicate class semantic name {name}: "
                    f"R{seen_names.get(name)} and R{batch}",
                )
                self.assertNotIn(
                    owner,
                    seen_owners,
                    f"duplicate class owner {owner}: "
                    f"R{seen_owners.get(owner)} and R{batch}",
                )
                self.assertNotIn(
                    stable_id,
                    seen_stable_ids,
                    f"duplicate class stable_id {stable_id}: "
                    f"R{seen_stable_ids.get(stable_id)} and R{batch}",
                )

                seen_names[name] = batch
                seen_owners[owner] = batch
                seen_stable_ids[stable_id] = batch


if __name__ == "__main__":
    unittest.main()
