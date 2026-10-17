"""R265 source-grounded v309 opcode-81 local-player teleport payload.

Independent local test fixture, not a general SpawnPK game server or an original
client source publication. Client.updateLocalPlayerMovement reads bits in MSB
order; one 8-bit other-player count follows. A zero update-mask bit means no
extra appearance masks are required. All state is test-only.
"""

def teleport_payload(local_x: int, local_y: int, plane: int = 0) -> bytes:
    if not 0 <= local_x <= 103 or not 0 <= local_y <= 103 or not 0 <= plane <= 3:
        raise ValueError("local tile outside scene")
    bits = ("1" "11" + f"{plane:02b}" + "1" "0"
            + f"{local_y:07b}" + f"{local_x:07b}" + "00000000")
    return int(bits.ljust(32, "0"), 2).to_bytes(4, "big")


def decode_teleport_payload(data: bytes) -> dict:
    if len(data) != 4:
        raise ValueError("expected four bytes")
    n = int.from_bytes(data, "big")
    widths = (1, 2, 2, 1, 1, 7, 7, 8)
    labels = ("updated", "movement_type", "plane", "clear_path",
              "update_mask", "local_y", "local_x", "other_players")
    offset = 32
    fields = {}
    for label, width in zip(labels, widths):
        offset -= width
        fields[label] = (n >> offset) & ((1 << width) - 1)
    if fields["updated"] != 1 or fields["movement_type"] != 3:
        raise ValueError("not a local teleport")
    return fields


if __name__ == "__main__":
    for x, y in ((0, 0), (48, 48), (52, 52), (103, 103)):
        data = teleport_payload(x, y)
        recovered = decode_teleport_payload(data)
        assert recovered["local_x"] == x and recovered["local_y"] == y
        assert recovered["other_players"] == 0 and recovered["plane"] == 0
    assert teleport_payload(52, 52).hex() == "e4d1a000"
    print("R265_TELEPORT_PAYLOAD_PASS cases=5")
