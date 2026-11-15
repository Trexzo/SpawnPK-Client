"""R418 invented read-only restart-to-UI reconciliation contract.

No recovered Java/client UI integration, OS lease acquisition, history writes,
acknowledgment cleanup, or autosave unblocking. A production caller must keep
one cooperative lease continuously held during stage and apply.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from tools.r417 import restart_ack_model as intent


@dataclass(frozen=True)
class Candidate:
    session: str
    generation: int
    marker_sha: str
    history_sha: str
    records: tuple[bytes, ...]


class Panel:
    """Synthetic panel; does not hold real player history."""

    def __init__(self):
        self.session: str | None = None
        self.generation = 0
        self.records: list[dict] = []
        self.pending_local_records = 0
        self.accepted_history_sha: str | None = None

    def start(self, owner_token: str) -> None:
        if not owner_token:
            raise ValueError("missing-session-token")
        self.session = owner_token
        self.generation += 1
        self.records = []
        self.pending_local_records = 0
        self.accepted_history_sha = None

    def revoke(self) -> None:
        self.session = None
        self.generation += 1

    def snapshot(self) -> tuple:
        return (self.session, self.generation,
                tuple(json.dumps(r, sort_keys=True) for r in self.records),
                self.pending_local_records, self.accepted_history_sha)

    def stage(self, directory: Path) -> Candidate | None:
        if self.session is None:
            return None
        evidence = intent.inspect(directory)
        if evidence.state not in (intent.COMMITTED, intent.ACKED):
            return None
        payload = intent._regular(Path(directory) / intent.HISTORY, intent.MAX_HISTORY)
        if payload is None or sha256(payload).hexdigest() != evidence.history_sha:
            return None
        try:
            value = json.loads(payload.decode("utf-8", "strict"))
            if not intent._valid_json_exact(payload):
                return None
            records = tuple(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                for row in value["records"])
        except (ValueError, TypeError, KeyError, UnicodeError):
            return None
        if intent.inspect(directory) != evidence:
            return None
        return Candidate(self.session, self.generation,
                         evidence.marker_sha, evidence.history_sha, records)

    def apply(self, directory: Path, candidate: Candidate, owner_token: str) -> str:
        if self.session is None or owner_token != self.session:
            return "REFUSED_OWNER"
        if candidate.session != self.session or candidate.generation != self.generation:
            return "REFUSED_STALE_SESSION"
        if self.pending_local_records:
            return "REFUSED_LOCAL_MUTATION"
        evidence = intent.inspect(directory)
        if (evidence.state not in (intent.COMMITTED, intent.ACKED)
                or evidence.marker_sha != candidate.marker_sha
                or evidence.history_sha != candidate.history_sha):
            return "REFUSED_CHANGED_DISK"
        if self.accepted_history_sha is not None:
            if self.accepted_history_sha == candidate.history_sha:
                return "ALREADY_APPLIED"
            return "REFUSED_PREVIOUS_ADOPTION"
        payload = intent._regular(Path(directory) / intent.HISTORY, intent.MAX_HISTORY)
        if payload is None or sha256(payload).hexdigest() != candidate.history_sha:
            return "REFUSED_CHANGED_DISK"
        try:
            data = json.loads(payload.decode("utf-8", "strict"))
            if (not intent._valid_json_exact(payload)
                    or tuple(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                             for row in data["records"]) != candidate.records):
                return "REFUSED_CHANGED_SCHEMA"
            replacement = [json.loads(row) for row in candidate.records]
        except (ValueError, TypeError, UnicodeError):
            return "REFUSED_CHANGED_SCHEMA"
        if intent.inspect(directory) != evidence:
            return "REFUSED_CHANGED_DISK"

        # Full replacement is intentional: multiple distinct drops may have
        # the same source/title. Never deduplicate by equality or title.
        self.records = replacement
        self.accepted_history_sha = candidate.history_sha
        return "APPLIED_READ_ONLY_FENCED"


def normal_writes_admitted(_panel: Panel) -> bool:
    return False  # Even successful UI restore NEVER authorizes persistence.
