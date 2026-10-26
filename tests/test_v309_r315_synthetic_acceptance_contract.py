"""R315 public source-only acceptance-shape tests.

Synthetic contract tests: no private Java, owner cache, real GUI or game
networking is executed. Real R315 GUI replay evidence is owner-private.
"""
import hashlib
import unittest


def verify_synthetic_receipt(seconds, actions, responses, outgoing, digest,
                             walk_confirmed, walk_packet_count, cleanup_count):
    if not (110 <= seconds < 145):
        raise ValueError("R315_110_SECOND_WORLD_MISSING")
    if len(actions) != 3 or any(tuple(a) != (132, 6, 114, 3362, 4769) for a in actions):
        raise ValueError("R315_THREE_REAL_OBJECT_ACTIONS_MISSING")
    if len(responses) != 3 or any(tuple(a) != (132, 253, 114) for a in responses):
        raise ValueError("R315_THREE_ACKNOWLEDGMENTS_MISSING")
    if len(outgoing) < 120 or hashlib.sha256(outgoing).hexdigest() != digest:
        raise ValueError("R315_WIRE_INTEGRITY_FAILED")
    if cleanup_count != 7:
        raise ValueError("R315_SEVEN_CHILD_CLEANUP_INCOMPLETE")
    if walk_confirmed and walk_packet_count == 0:
        raise ValueError("R315_FALSE_MOVEMENT_PROMOTION")
    return True


class R315SyntheticEvidenceContract(unittest.TestCase):
    def setUp(self):
        self.wire = b"synthetic-r315-only-" * 8
        self.k = dict(seconds=110.25,
            actions=[(132, 6, 114, 3362, 4769)] * 3,
            responses=[(132, 253, 114)] * 3,
            outgoing=self.wire, digest=hashlib.sha256(self.wire).hexdigest(),
            walk_confirmed=False, walk_packet_count=0, cleanup_count=7)

    def check(self, **kw):
        k = dict(self.k)
        k.update(kw)
        return verify_synthetic_receipt(**k)

    def test_complete_no_walk_claim(self):
        self.assertTrue(self.check())

    def test_75_second_replay_refused(self):
        with self.assertRaisesRegex(ValueError, "110_SECOND"):
            self.check(seconds=75.2)

    def test_missing_third_real_packet_refused(self):
        with self.assertRaisesRegex(ValueError, "THREE_REAL"):
            self.check(actions=self.k["actions"][:2])

    def test_missing_third_ack_refused(self):
        with self.assertRaisesRegex(ValueError, "THREE_ACK"):
            self.check(responses=self.k["responses"][:2])

    def test_changed_wire_refused(self):
        with self.assertRaisesRegex(ValueError, "WIRE_INTEGRITY"):
            self.check(outgoing=self.wire[:-1] + b"x")

    def test_wrong_child_count_refused(self):
        with self.assertRaisesRegex(ValueError, "SEVEN_CHILD"):
            self.check(cleanup_count=5)

    def test_walk_click_must_not_promote_to_movement(self):
        with self.assertRaisesRegex(ValueError, "FALSE_MOVEMENT"):
            self.check(walk_confirmed=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
