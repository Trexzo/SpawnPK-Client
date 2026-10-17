import socket
import threading
import time
import unittest
from tools.r248_loopback_success_probe import run

class ProbeTests(unittest.TestCase):
    def scenario(self, mode):
        with socket.socket() as tmp:
            tmp.bind(("127.0.0.1", 0))
            port = tmp.getsockname()[1]
        observed = {}
        def server():
            try:
                observed.update(run(port, mode, timeout=3))
            except Exception as exc:
                observed["error"] = str(exc)
        worker = threading.Thread(target=server)
        worker.start()
        time.sleep(0.1)
        with socket.create_connection(("127.0.0.1", port), timeout=3) as client:
            client.sendall(bytes([14, 29]))
            initial = b""
            while len(initial) < 17:
                initial += client.recv(17 - len(initial))
            self.assertEqual(len(initial), 17)
            client.sendall(bytes([16, 4, 1, 2, 3, 4]))
            response = client.recv(1)
            self.assertEqual(response, bytes([2 if mode == "success" else 3]))
            if mode == "success":
                self.assertEqual(client.recv(2), bytes([0, 0]))
                client.sendall(bytes([0xAB, 0xCD]))
        worker.join(timeout=4)
        self.assertFalse(worker.is_alive())
        self.assertNotIn("error", observed)
        self.assertTrue(observed["handshake"])
        self.assertTrue(observed["frame"])
        self.assertEqual(observed["response"], 2 if mode == "success" else 3)
        if mode == "success":
            self.assertGreater(observed["post_success_bytes"], 0)

    def test_success(self):
        self.scenario("success")

    def test_reject(self):
        self.scenario("reject")

if __name__ == "__main__":
    unittest.main()
