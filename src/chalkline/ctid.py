"""CTIDs that follow the published grammar, kept stable by a ledger rather than by derivation.

Credential Engine's CTID page (https://credreg.net/ctdl/ctid, retrieved 2026-08-07) states
the grammar exactly:

    "Each CTID is made up of a standard UUID v4 prefixed with ``ce-``. The standard 16
    octets of a UUID are represented as 32 hexadecimal (base-16) digits, displayed in five
    groups separated by hyphens, in the form 8-4-4-4-12 for a total of 36 characters (32
    hexadecimal characters and 4 hyphens). When the UUID is prefixed with ``ce-``, there
    are a total of 34 hexadecimal characters and 5 hyphens for a total of 39 characters."

Version 4 means random. That is in obvious tension with wanting a re-export to reproduce the
same identifiers, and the usual shortcut is to derive a UUIDv5 from a namespace and a key:
deterministic, idempotent, and not what the spec says. This project takes the other road.

**Identifiers here are real UUIDv4s, minted once and then committed.** ``data/ctid-ledger.json``
maps each authorization's published triple to the CTID assigned to it. Minting happens only
when someone runs ``chalkline mint-ctids``; the export refuses to invent one, so a CTID can
never appear as a side effect of a build. Re-export is idempotent because the ledger is in
version control, which is the same reason a registry's CTIDs are stable: somebody wrote them
down. The tension the v5 shortcut papers over is resolved by persistence instead of by
weakening the identifier.

These are still **not Registry-assigned CTIDs**. A CTID becomes meaningful when a registry
assigns it to a resource it holds, and nothing here is published to any registry. What the
ledger demonstrates is that a publisher can hold spec-conformant, stable identifiers for its
own credential inventory before it ever publishes, which is the position CTC would be in.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Final

LEDGER_PATH: Final = Path(__file__).resolve().parents[2] / "data" / "ctid-ledger.json"

CTID_RE: Final = re.compile(
    r"^ce-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
"""The published grammar, enforced. The ``4`` fixes the version nibble and ``[89ab]`` the
variant bits, which is what makes a UUID a standard v4 rather than 32 arbitrary hex digits."""

LEDGER_NOTE: Final = (
    "CTIDs minted by this project for its own demonstration export. Each is a standard "
    "UUID v4 prefixed with ce-, per https://credreg.net/ctdl/ctid. They are stable because "
    "this file is committed, not because they are derived from the key beside them. None of "
    "them is assigned by the Credential Registry, and nothing here has been published to it."
)


def is_ctid(value: str) -> bool:
    """Whether a string conforms to the published CTID grammar."""
    return bool(CTID_RE.fullmatch(value))


def mint() -> str:
    """A new spec-conformant CTID: ``ce-`` plus a standard UUID v4."""
    return f"ce-{uuid.uuid4()}"


def load_ledger(path: Path | None = None) -> dict[str, str]:
    """The committed key-to-CTID mapping, validated on the way in.

    A malformed entry stops everything here rather than reaching an export, because a CTID
    that does not match the grammar is the exact bug this project exists to not demonstrate.

    Two different absences, kept apart. **No ledger file** is a real state: a repository
    before its first mint has none, and reading that as an empty mapping is correct. **A
    ledger file that does not hold a ``ctids`` mapping** is not that state; it is a file
    this function cannot read. Both used to arrive here as ``{}``, and the difference
    matters because of what the empty mapping is then used for: `mint_missing` treats every
    key as unassigned, mints a fresh UUIDv4 for each, and `save_ledger` writes the result
    over the file. A ledger whose ``ctids`` key had been renamed, dropped in a merge, or
    truncated away would therefore be *repaired* by re-minting all 134 identifiers, exiting
    0 and reporting the new count as a successful run, with none of the committed CTIDs
    surviving. Stability here rests on the file, so a file that cannot be read has to stop
    the run rather than read as a blank slate.
    """
    ledger_path = path or LEDGER_PATH
    if not ledger_path.exists():
        return {}
    document = json.loads(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError(
            f"the ledger at {ledger_path} holds a {type(document).__name__}, not an object; "
            "a ledger that cannot be read is not a ledger with nothing in it"
        )
    if "ctids" not in document:
        raise ValueError(
            f"the ledger at {ledger_path} holds no 'ctids' key. An absent mapping is not an "
            "empty one: minting against it would re-mint every identifier and overwrite the "
            "assignments this file exists to keep stable. Restore the file, or delete it to "
            "start a ledger from nothing."
        )
    assignments = document["ctids"]
    if not isinstance(assignments, Mapping):
        raise ValueError(
            f"the ledger at {ledger_path} maps 'ctids' to a {type(assignments).__name__}, "
            "not an object of key-to-CTID assignments"
        )
    ctids: dict[str, str] = dict(assignments)
    # A non-string value reaches `is_ctid` as a regex argument and raises TypeError from the
    # `re` module, which names neither this file nor the key at fault. It is a value that is
    # not a CTID, so it is reported as one.
    bad = {
        key: value
        for key, value in ctids.items()
        if not isinstance(value, str) or not is_ctid(value)
    }
    if bad:
        raise ValueError(f"ledger holds values that are not CTIDs: {sorted(bad)[:5]}")
    duplicated = [value for value in set(ctids.values()) if list(ctids.values()).count(value) > 1]
    if duplicated:
        raise ValueError(f"ledger assigns the same CTID to more than one key: {duplicated[:5]}")
    return ctids


def save_ledger(ctids: Mapping[str, str], path: Path | None = None) -> None:
    """Write the ledger, key-sorted, so a mint produces a reviewable diff."""
    ledger_path = path or LEDGER_PATH
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    document = {"note": LEDGER_NOTE, "ctids": {key: ctids[key] for key in sorted(ctids)}}
    ledger_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def mint_missing(keys: Iterable[str], ctids: Mapping[str, str]) -> tuple[dict[str, str], int]:
    """The ledger extended to cover ``keys``, and how many CTIDs that took.

    Existing assignments are never re-minted: an identifier that has been handed out, even
    only inside this repository, does not get to change quietly.
    """
    updated = dict(ctids)
    minted = 0
    for key in keys:
        if key not in updated:
            updated[key] = mint()
            minted += 1
    return updated, minted


def require(key: str, ctids: Mapping[str, str]) -> str:
    """The CTID for ``key``, or a refusal that names the fix.

    The export calls this. It never falls back to minting, because a CTID that appears
    during a build is one nobody decided to assign.
    """
    try:
        return ctids[key]
    except KeyError:
        raise KeyError(
            f"no CTID in the ledger for {key!r}. Run `chalkline mint-ctids` to assign one "
            "and commit the result; the export will not mint identifiers on its own."
        ) from None
