"""Original-independent R314 acceptance receipt contract — SYNTHETIC tests only.

These tests deliberately do not load proprietary game code, assets, or a server.
Passing public CI does not establish native original-client runtime parity.
"""
import hashlib
import unittest

def check_receipt(timeline, actions, acks, wire, expected_sha, screenshots):
    if not timeline or timeline[0] > 41 or timeline[-1] < 75:
        raise ValueError("R314_MISSING_75_SECOND_WORLD_CHECKPOINT")
    if sorted(timeline) != timeline or len(timeline) != 4:
        raise ValueError("R314_NONMONOTONIC_WORLD_CHECKPOINTS")
    if len(actions) != 2 or len(acks) != 2:
        raise ValueError("R314_TWO_REAL_OBJECT_ACTIONS_REQUIRED")
    if any(tuple(a) != (132, 6, 114, 3362, 4769) for a in actions):
        raise ValueError("R314_REAL_ACTION_FIELDS_DRIFT")
    if any(tuple(a) != (132, 253, 114) for a in acks):
        raise ValueError("R314_SERVER_ACK_FIELDS_DRIFT")
    if len(wire) < 90 or hashlib.sha256(wire).hexdigest() != expected_sha:
        raise ValueError("R314_CAPTURED_WIRE_INTEGRITY_FAILED")
    if sorted(screenshots) != [40, 55, 70, 75]:
        raise ValueError("R314_SCREENSHOT_CHECKPOINT_MISSING")
    return True


class R314SyntheticContract(unittest.TestCase):
    def setUp(self):
        self.t = [40.2, 55.1, 70.3, 75.2]
        self.a = [(132, 6, 114, 3362, 4769)] * 2
        self.k = [(132, 253, 114)] * 2
        self.w = b"synthetic-no-client-packets-" * 5
        self.h = hashlib.sha256(self.w).hexdigest()
        self.s = [40, 55, 70, 75]

    def check(self, **changes):
        d = {"timeline":self.t, "actions":self.a, "acks":self.k,
             "wire":self.w, "expected_sha":self.h, "screenshots":self.s}
        d.update(changes)
        return check_receipt(**d)

    def test_synthetic_complete(self):
        self.assertTrue(self.check())

    def test_missing_second_real_action_refused(self):
        with self.assertRaisesRegex(ValueError, "TWO_REAL"):
            self.check(actions=self.a[:1])

    def test_missing_second_server_ack_refused(self):
        with self.assertRaisesRegex(ValueError, "TWO_REAL"):
            self.check(acks=self.k[:1])

    def test_short_observation_refused(self):
        with self.assertRaisesRegex(ValueError, "75_SECOND"):
            self.check(timeline=[20, 30, 40, 41])

    def test_wrong_action_coordinates_refused(self):
        with self.assertRaisesRegex(ValueError, "FIELDS_DRIFT"):
            self.check(actions=[self.a[0],(132, 6, 114, 3362, 4770)])

    def test_missing_late_screenshot_refused(self):
        with self.assertRaisesRegex(ValueError, "SCREENSHOT"):
            self.check(screenshots=[40, 55, 70])

    def test_wire_corruption_refused(self):
        with self.assertRaisesRegex(ValueError, "WIRE_INTEGRITY"):
            self.check(wire=self.w[:-1]+b"x")


if __name__ == "__main__":
    unittest.main(verbosity=2)
