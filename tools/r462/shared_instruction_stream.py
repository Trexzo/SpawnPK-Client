"""R462 class-local immutable JVM instruction boundary reuse.

Never caches outside the current compiled-class evidence pass. A cache entry
is keyed by the EXACT method Code bytes, not a filename or method label:
identical byte streams have identical JVM instruction boundaries.

Only decoded instruction tuples are shared. Each independent observer still
checks its own constant-pool operands, descriptors, method properties and
resource/dataflow evidence; original full SHA observations are unchanged.
"""
from __future__ import annotations


class Refused(ValueError):
    pass


MAX_CODE_BYTES = 65535
MAX_DISTINCT_CODE_BODIES = 60000
MAX_TOTAL_CODE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_INSTRUCTIONS = 1_000_000


class Index:
    __slots__ = ("_streams", "misses", "hits", "bytes_decoded",
                 "instructions_decoded")

    def __init__(self):
        self._streams: dict[bytes, tuple[tuple[int, int, bytes], ...]] = {}
        self.misses = 0
        self.hits = 0
        self.bytes_decoded = 0
        self.instructions_decoded = 0


def decode(index: Index, code: bytes, original_decoder):
    """Use canonical R450 parser once per distinct method Code byte stream."""
    if type(index) is not Index or type(code) is not bytes or (
            len(code) > MAX_CODE_BYTES):
        raise Refused("R462_INSTRUCTION_INDEX_INPUT_REFUSED")
    found = index._streams.get(code)
    if found is not None:
        index.hits += 1
        return found
    if len(index._streams) >= MAX_DISTINCT_CODE_BODIES or (
            index.bytes_decoded + len(code) > MAX_TOTAL_CODE_BYTES):
        raise Refused("R462_INSTRUCTION_INDEX_CLASS_BUDGET")
    decoded = original_decoder(code)
    # Re-validate structural shape before inserting a reusable immutable
    # sequence; do not cache malformed bytecode or partial decoder output.
    if type(decoded) is not list or any(
            type(site) is not tuple or len(site) != 3
            or type(site[0]) is not int or type(site[1]) is not int
            or type(site[2]) is not bytes for site in decoded):
        raise Refused("R462_INSTRUCTION_DECODER_RESULT_INVALID")
    frozen = tuple(decoded)
    if index.instructions_decoded + len(frozen) > MAX_TOTAL_INSTRUCTIONS:
        raise Refused("R462_INSTRUCTION_INDEX_OPCODE_BUDGET")
    index._streams[code] = frozen
    index.misses += 1
    index.bytes_decoded += len(code)
    index.instructions_decoded += len(frozen)
    return frozen
