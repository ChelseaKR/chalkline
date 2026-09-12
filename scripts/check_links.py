#!/usr/bin/env python3
"""Record what one run observes about each Commission URL this graph publishes.

Run by hand, on a human's schedule (quarterly is the intent), never by `make verify`,
never by CI, never by the test suite. It is the third file in this repository that opens
a socket, alongside ``scripts/fetch_sources.py`` and ``scripts/verify_live_site.py``, and
``tests/test_provenance.py`` holds that list to exactly three so a fourth cannot appear
without this docstring being wrong out loud.

    make check-links                 # check every URL with no recent verdict
    make check-links ARGS=--all      # re-check every URL regardless of age

**There is no `chalkline check-links` verb, deliberately.** The obvious place for this is
the CLI, and the CLI is in ``src/chalkline/``, where ``tests/test_provenance.py`` fails any
module that imports a networking module. It counts ``subprocess`` too, on the reasoning that
shelling out to `curl` reaches the network by asking another program to, so a verb that
delegated to this script would fail the same scan. The scan is what makes the README's
network-posture claim checkable, and the claim is worth more than the verb. What lives in
the package is ``chalkline.links``, which reads the file this script writes and opens
nothing.

**What a verdict is.** One request, from one machine, at one time. ``unreachable`` means
this run could not reach the URL; it is not a statement that the Commission's page is gone,
and nothing here ever phrases it as one. ``indeterminate`` exists so that a response this
run could not interpret is filed as uninterpreted rather than as somebody's failure.

**What a verdict never does.** It never changes a URL. A redirect is recorded with its
final address and the graph keeps publishing the address the Commission published, because
the Commission's published address is the fact this project is modeling.

**The cache is the verdict file itself.** A URL whose recorded verdict is younger than
``EXPIRY_DAYS`` is skipped and its row carried forward unchanged, so a re-run costs one
request per stale URL rather than one per URL. ``--all`` ignores that.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from chalkline import links as links_module  # noqa: E402

GRAPH_PATH: Final = REPO_ROOT / "site" / "credentials.jsonld"

PAUSE_SECONDS: Final = 2.0
"""Held between consecutive requests, for the same reason `fetch_sources.py` holds one.

Nothing here has ever been rate-limited. The only cost of waiting is this script's own
wall clock, and issuing a dozen requests to one small state agency as fast as the
interpreter can is not the same thing as issuing them politely.
"""

TIMEOUT_SECONDS: Final = 30
ATTEMPTS: Final = 2
"""One retry, and only for a transport failure. A refusal is an answer, not a rate limit."""

EXPIRY_DAYS: Final = 80
"""How long a recorded verdict is reused before a re-run requests the URL again.

Deliberately shorter than the quarter this check is meant to run on, so a quarterly run
never finds its own previous verdicts still fresh and does nothing.
"""

USER_AGENT: Final = (
    "chalkline/0.1 (+https://github.com/ChelseaKR/chalkline) "
    "quarterly link check for an unofficial CTDL modeling demonstration"
)

_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_MAX_TITLE_BYTES: Final = 65_536


def _title_of(payload: bytes) -> str | None:
    """The page's own ``<title>``, read from the head, or ``None``."""
    match = _TITLE.search(payload[:_MAX_TITLE_BYTES].decode("utf-8", errors="replace"))
    if match is None:
        return None
    return " ".join(match.group(1).split())[:200] or None


def _verdict_for(url: str, final_url: str) -> str:
    """Classify a successful response by where it ended up."""
    if final_url == url:
        return links_module.ALIVE
    if urlsplit(final_url).netloc == links_module.COMMISSION_HOST:
        return links_module.REDIRECTED_ON_SITE
    return links_module.REDIRECTED_OFF_SITE


def check(url: str, today: str) -> links_module.Verdict:
    """Request one URL once (twice on a transport failure) and record what happened."""
    if not url.startswith("https://"):
        raise ValueError(f"refusing to request {url!r}: only https URLs are checked")
    last_reason = ""
    for attempt in range(ATTEMPTS):
        # nosemgrep: dynamic-urllib-use-detected - scheme is pinned to https above
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
        try:
            # nosemgrep: dynamic-urllib-use-detected - scheme is pinned to https above
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
                final_url = response.geturl()
                payload = response.read(_MAX_TITLE_BYTES)
            return links_module.Verdict(
                url=url,
                verdict=_verdict_for(url, final_url),
                checked=today,
                status=200,
                final_url=final_url,
                title=_title_of(payload),
            )
        except urllib.error.HTTPError as error:
            # A status is an answer. It is recorded once and not asked again.
            return links_module.Verdict(
                url=url,
                verdict=links_module.UNREACHABLE
                if error.code >= 400
                else links_module.INDETERMINATE,
                checked=today,
                status=error.code,
                final_url=None,
                title=None,
            )
        except urllib.error.URLError as error:  # pragma: no cover - network failure path
            last_reason = str(error.reason)
            if attempt + 1 < ATTEMPTS:
                time.sleep(PAUSE_SECONDS)
    # Neither reached nor refused. This run learned nothing, and says so rather than
    # filing a failure against the Commission for a socket this machine could not open.
    print(f"  {url}: {last_reason}", file=sys.stderr)
    return links_module.Verdict(
        url=url,
        verdict=links_module.INDETERMINATE,
        checked=today,
        status=None,
        final_url=None,
        title=None,
    )


def _stale(entry: links_module.Verdict | None, today: date) -> bool:
    """Whether this URL has to be requested again, in three states rather than two.

    Within the expiry, past it, and **not usable as an age at all**. The third
    is the one that hides: a row dated after ``today`` gives a negative age, and
    a negative age is inside every expiry there will ever be, so a verdict
    written by a run on a machine whose clock was ahead would be carried
    forward by every later run for good, never re-requested, while
    ``links.page_note`` goes on describing the file as a run that observed
    those URLs. This module's own docstring calls the verdict file a cache; a
    cache entry that can never expire is the failure that idea has.

    ``chalkline.links.parse`` refuses a row dated after the *file's own stamp*,
    which is the clock-free half of the same rule and catches a hand-edit. This
    is the other half: a run whose whole file was written under a wrong clock
    is internally consistent, and only a later run with a correct one can see
    it.
    """
    if entry is None:
        return True
    recorded = date.fromisoformat(entry.checked)
    if recorded > today:
        return True
    return recorded <= today - timedelta(days=EXPIRY_DAYS)


def _unusable_date(entry: links_module.Verdict | None, today: date) -> str:
    """Why this row's date could not be read as an age, or ``""`` when it could.

    Said out loud on the run's own output, beside the request it causes. A row
    re-requested for this reason looks exactly like an expired one from the
    outside, and an operator who cannot tell them apart cannot go and fix the
    clock or the row that produced it. Names the row, the date and the file the
    caller passes.
    """
    if entry is None:
        return ""
    recorded = date.fromisoformat(entry.checked)
    if recorded <= today:
        return ""
    return (
        f"its recorded date {entry.checked} is after today ({today.isoformat()}), "
        f"so its age is negative and no expiry can ever reach it; re-requesting. "
        f"Check the clock on the machine that wrote it."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all",
        action="store_true",
        help="re-check every URL, ignoring verdicts that are still within the expiry",
    )
    parser.add_argument("--graph", type=Path, default=GRAPH_PATH)
    parser.add_argument("--output", type=Path, default=links_module.VERDICT_PATH)
    args = parser.parse_args(argv)

    document = json.loads(args.graph.read_text(encoding="utf-8"))
    urls = links_module.commission_urls(document)
    if not urls:
        print(f"{args.graph} publishes no {links_module.COMMISSION_HOST} URLs.", file=sys.stderr)
        return 1

    existing = links_module.load(args.output)
    carried = existing.by_url() if existing is not None else {}
    today = date.today()
    stamp = today.isoformat()

    entries: list[links_module.Verdict] = []
    requested = 0
    print(f"{len(urls)} distinct {links_module.COMMISSION_HOST} URLs in {args.graph.name}")
    for url in urls:
        previous = carried.get(url)
        if not args.all and not _stale(previous, today) and previous is not None:
            entries.append(previous)
            print(f"  kept  {previous.verdict:<20} {url} (checked {previous.checked})")
            continue
        unusable = _unusable_date(previous, today)
        if unusable:
            print(f"  {args.output}: {url}: {unusable}", file=sys.stderr)
        if requested:
            time.sleep(PAUSE_SECONDS)
        entry = check(url, stamp)
        requested += 1
        entries.append(entry)
        print(f"  saw   {entry.verdict:<20} {url}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        links_module.serialize(links_module.Verdicts(checked=stamp, entries=tuple(entries))),
        encoding="utf-8",
    )
    print(
        f"this run requested {requested} of {len(urls)} URLs and wrote {args.output}. "
        "Rebuild and review the diff; nothing here changes a URL the graph publishes."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main())
