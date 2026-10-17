#!/usr/bin/env python3
"""Loopback-only, bounded v309 test login listener. Never log credential payload."""
import argparse, json, socket

def exact(conn, n):
    data = b""
    while len(data) < n:
        part = conn.recv(n - len(data))
        if not part:
            raise EOFError("truncated login frame")
        data += part
    return data

def run(port=43594, mode="success", timeout=8):
    report = {"handshake": False, "frame": False, "response": None, "post_success_bytes": 0}
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", port))
        srv.listen(1)
        srv.settimeout(timeout)
        conn, peer = srv.accept()
        with conn:
            conn.settimeout(timeout)
            if peer[0] != "127.0.0.1":
                raise ValueError("non-loopback source")
            hello = exact(conn, 2)
            if hello[0] != 14:
                raise ValueError("not a login handshake")
            report["handshake"] = True
            conn.sendall(bytes(8) + bytes([0]) + bytes.fromhex("0000000000000001"))
            opcode, size = exact(conn, 2)
            if opcode not in (16, 18):
                raise ValueError("not a login packet")
            credential_payload = exact(conn, size)
            report["frame"] = len(credential_payload) == size
            del credential_payload
            code = 2 if mode == "success" else 3
            conn.sendall(bytes([code, 0, 0]) if code == 2 else bytes([code]))
            report["response"] = code
            if code == 2:
                conn.settimeout(min(timeout, 3))
                try:
                    report["post_success_bytes"] = len(conn.recv(2048))
                except socket.timeout:
                    report["timed_out_after_success"] = True
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=43594)
    parser.add_argument("--mode", choices=["success", "reject"], default="success")
    args = parser.parse_args()
    print(json.dumps(run(args.port, args.mode), indent=2))
