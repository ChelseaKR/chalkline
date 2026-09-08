"""Link verdicts: what a run observed about the Commission URLs this graph publishes.

Nothing in this module opens a socket, and nothing in it may. The requests are
made by ``scripts/check_links.py``, by hand, and this reads what that run wrote.
That split is not tidiness: ``tests/test_provenance.py`` scans every module under
``src/chalkline/`` for a networking import and fails on one, and README.md and
PROVENANCE.md make a repository-wide claim about which files reach the network.
Putting the fetch here would break both, and a ``chalkline check-links`` verb
that shelled out to the script would break the first as well, because the
package scan counts ``subprocess`` as reaching the network by asking another
program to.

Three rules the vocabulary exists to enforce.

**A verdict is about one run, from one machine, at one time.** ``unreachable``
means this run could not reach the URL. It does not mean the Commission's page is
gone. Only the first is supportable from a single request, and every string this
module produces is phrased as the first.

**A blocked read is not a fact.** ``indeterminate`` exists so that a response
this run could not interpret is filed as uninterpreted rather than as a failure
the Commission owns.

**No verdict file is not a clean bill of health.** A build with no
``data/link-verdicts.json`` publishes every URL as filed and says exactly that.
It must never render as "0 unreachable": zero-unreachable and not-checked are
different statements, and only the second one is true.

**Nor is a verdict file.** The same rule applies one level down, and it did not
used to. ``Verdicts.checked`` is the date the *file* was written, and
``scripts/check_links.py`` writes it on every run while carrying forward every
verdict younger than its expiry. So a second quarterly run inside the expiry
requests nothing at all and restamps the file with the day it ran, and the note
built from that stamp read "A link check run on <today> requested each distinct
Commission URL once. It observed 14 reachable" over fourteen observations up to
eighty days old and zero requests. The window below is therefore read from the
rows, which each carry the date they were recorded, and never from the stamp.
A published URL that no row covers is named for the same reason: ``summary``
has counted it since the module was written, and the sentence a reader actually
gets used to leave it out, so thirteen observations were published under a
sentence claiming each of fourteen URLs had been requested.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Final

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
VERDICT_PATH: Final = REPO_ROOT / "data" / "link-verdicts.json"

COMMISSION_HOST: Final = "www.ctc.ca.gov"
COMMISSION_ORIGIN: Final = f"https://{COMMISSION_HOST}"
"""The one origin these verdicts are about. Every other URL in the graph is this
project's own or a specification's, and neither is the Commission's to move."""


def is_commission_url(value: str) -> bool:
    """Is this exactly a URL on the Commission's site?

    Matched by origin prefix rather than by parsing, because `urllib.parse` is a
    networking import as far as `tests/test_provenance.py`'s package scan is
    concerned, and that scan is worth more than the convenience. Requiring the
    origin to be followed by ``/`` or nothing is what keeps
    ``https://www.ctc.ca.gov.example.invalid/`` and
    ``https://www.ctc.ca.gov@example.invalid/`` out; both fail closed, which is
    the direction to fail in when the question is "should this be requested".
    """
    return value == COMMISSION_ORIGIN or value.startswith(f"{COMMISSION_ORIGIN}/")


ALIVE: Final = "alive"
REDIRECTED_ON_SITE: Final = "redirected on-site"
REDIRECTED_OFF_SITE: Final = "redirected off-site"
UNREACHABLE: Final = "unreachable"
INDETERMINATE: Final = "indeterminate"

VERDICTS: Final[tuple[str, ...]] = (
    ALIVE,
    REDIRECTED_ON_SITE,
    REDIRECTED_OFF_SITE,
    UNREACHABLE,
    INDETERMINATE,
)

NOT_CHECKED: Final = "not_checked"
RECORDED: Final = "recorded"

#: Printed and published wherever no verdict file exists. The sentence says what
#: was not done, because the alternative is a page that looks checked.
NOT_CHECKED_NOTE: Final = (
    "No link check has been run. Every Commission URL below is published as filed, "
    "and none of them has been requested by this project. That is not the same "
    "statement as every link working."
)

#: How a recorded run is described when every observation was made on one day.
#: The subject of every clause is the run, and the coverage is stated rather than
#: assumed: "each distinct Commission URL" was a claim about the graph that only
#: the run's own arithmetic could support, and it did not.
RECORDED_NOTE: Final = (
    "A link check run on {first} requested {covered} of the {published} distinct "
    "Commission URLs this graph publishes, once each. It observed {alive} reachable, "
    "{redirected} redirected, {unreachable} that it could not reach, and "
    "{indeterminate} it could not interpret. A redirect is annotated and never "
    "rewritten: the address the Commission publishes stays the address this graph "
    "publishes."
)

#: The same sentence when the observations were not all made on one day, which is
#: the ordinary case after the first run: a verdict is reused until it expires
#: rather than re-requested, so the file's own date is the date it was written and
#: not the date anything was observed.
RECORDED_SPAN_NOTE: Final = (
    "Link check runs recorded between {first} and {last} requested {covered} of the "
    "{published} distinct Commission URLs this graph publishes, once each. They "
    "observed {alive} reachable, {redirected} redirected, {unreachable} they could "
    "not reach, and {indeterminate} they could not interpret. A verdict is reused "
    "until it expires rather than re-requested, so those are the dates the "
    "observations were made and not the date the file was written. A redirect is "
    "annotated and never rewritten: the address the Commission publishes stays the "
    "address this graph publishes."
)

#: Appended whenever the graph publishes a URL that no observation covers, which
#: happens as soon as the graph gains one after the last check was run. The count
#: sits after a colon rather than as the subject so that one uncovered URL and
#: five read the same sentence: this project already carries one two-branch plural
#: conditional (`docs/I18N.md` names it as the thing a catalog would have to hold
#: as a plural form), and a second one would be a second debt for no gain here.
PARTIAL_NOTE: Final = (
    " The rest are published as filed and have not been requested by this project: "
    "{uncovered} of the {published}."
)

#: Published in place of the counts when a verdict file covers none of the URLs the
#: graph publishes, so that a file about fourteen addresses the graph has since
#: stopped publishing cannot read as a check of the fourteen it publishes now.
NOTHING_COVERED_NOTE: Final = (
    "A link check has been recorded, and none of it is about the {published} "
    "Commission URLs this graph publishes now. Every one of them is published as "
    "filed and none has been requested by this project. That is not the same "
    "statement as every link working."
)


class VerdictError(ValueError):
    """A verdict file that cannot be read as one."""


@dataclass(frozen=True, slots=True)
class Verdict:
    """One URL, one observation, from one run."""

    url: str
    verdict: str
    checked: str
    status: int | None
    final_url: str | None
    title: str | None


@dataclass(frozen=True, slots=True)
class Verdicts:
    """Every observation a recorded run made, and the date it made them."""

    checked: str
    entries: tuple[Verdict, ...]

    def by_url(self) -> dict[str, Verdict]:
        return {entry.url: entry for entry in self.entries}


def _walk_strings(value: Any) -> Iterator[str]:
    """Every string anywhere in a JSON document, in document order."""
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _walk_strings(item)
    elif isinstance(value, str):
        yield value
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            yield from _walk_strings(item)


def commission_references(document: Mapping[str, Any]) -> list[str]:
    """Every Commission URL the graph publishes, once per occurrence.

    Walks every string in the document rather than a list of the properties that
    are known to hold URLs. A hand-kept list of where URLs live is exactly the
    thing that goes out of date when a property is added, and the failure would
    be silent: a new Commission URL published and never checked.
    """
    return [value for value in _walk_strings(document) if is_commission_url(value)]


def commission_urls(document: Mapping[str, Any]) -> list[str]:
    """The distinct Commission URLs, sorted. One request per entry, and no more."""
    return sorted(set(commission_references(document)))


def load(path: Path = VERDICT_PATH) -> Verdicts | None:
    """Read a verdict file, or return ``None`` when there is none.

    ``None`` is a real answer here and is carried all the way to the published
    page. It is deliberately not an empty :class:`Verdicts`, which would count
    zero of everything and be indistinguishable from a run that found nothing
    wrong.
    """
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerdictError(f"{path} is not readable as JSON") from exc
    return parse(raw)


def parse(raw: Any) -> Verdicts:
    """Validate a verdict document into observations, refusing anything unclear."""
    if not isinstance(raw, Mapping):
        raise VerdictError("a verdict file is a JSON object")
    checked = raw.get("checked")
    if not isinstance(checked, str):
        raise VerdictError("a verdict file states the date it was checked")
    try:
        date.fromisoformat(checked)
    except ValueError as exc:
        raise VerdictError("checked is an ISO-8601 date") from exc
    rows = raw.get("verdicts")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise VerdictError("a verdict file carries a non-empty list of verdicts")
    entries: list[Verdict] = []
    seen: set[str] = set()
    for row in rows:
        entry = _entry(row)
        if entry.url in seen:
            raise VerdictError(f"{entry.url} carries more than one verdict")
        seen.add(entry.url)
        entries.append(entry)
    return Verdicts(checked=checked, entries=tuple(sorted(entries, key=lambda e: e.url)))


def _entry(row: Any) -> Verdict:
    if not isinstance(row, Mapping):
        raise VerdictError("each verdict is a JSON object")
    url = row.get("url")
    verdict = row.get("verdict")
    checked = row.get("checked")
    if not isinstance(url, str) or not is_commission_url(url):
        raise VerdictError("each verdict names a Commission URL")
    if verdict not in VERDICTS:
        raise VerdictError(f"{verdict!r} is not one of {VERDICTS}")
    if not isinstance(checked, str):
        raise VerdictError(f"{url} states no date it was checked")
    try:
        date.fromisoformat(checked)
    except ValueError as exc:
        raise VerdictError(f"{url} states a checked date that is not ISO-8601") from exc
    status = row.get("status")
    if status is not None and (isinstance(status, bool) or not isinstance(status, int)):
        raise VerdictError(f"{url} states a status that is not an integer")
    final_url = row.get("final_url")
    title = row.get("title")
    for name, value in (("final_url", final_url), ("title", title)):
        if value is not None and not isinstance(value, str):
            raise VerdictError(f"{url} states a {name} that is not a string")
    return Verdict(
        url=url,
        verdict=verdict,
        checked=checked,
        status=status,
        final_url=final_url,
        title=title,
    )


@dataclass(frozen=True, slots=True)
class Coverage:
    """What a recorded run covers of the graph it is published beside.

    Every number here is counted over the URLs *this* graph publishes, so a
    verdict for an address the graph has dropped contributes to none of them,
    and a URL the graph has gained since the check contributes to ``published``
    and to nothing else. ``first`` and ``last`` come from the covering rows and
    not from :attr:`Verdicts.checked`, which is the date the file was written.
    """

    published: int
    covered: int
    counts: Mapping[str, int]
    first: str | None
    last: str | None

    @property
    def uncovered(self) -> int:
        """Published URLs no observation is about. Never rolled into a verdict."""
        return self.published - self.covered

    @property
    def one_day(self) -> bool:
        """Were every covering observation recorded on the same date?"""
        return self.covered > 0 and self.first == self.last


def coverage_of(document: Mapping[str, Any], verdicts: Verdicts) -> Coverage:
    """Count a verdict file against the graph, reading dates from the rows."""
    urls = commission_urls(document)
    by_url = verdicts.by_url()
    counts = {name: 0 for name in VERDICTS}
    dates: list[str] = []
    for url in urls:
        entry = by_url.get(url)
        if entry is None:
            continue
        counts[entry.verdict] += 1
        dates.append(entry.checked)
    return Coverage(
        published=len(urls),
        covered=len(dates),
        counts=counts,
        first=min(dates) if dates else None,
        last=max(dates) if dates else None,
    )


def summary(document: Mapping[str, Any], verdicts: Verdicts | None) -> dict[str, Any]:
    """The block published in ``coverage.json``, counted from the graph beside it.

    ``references_published`` and ``urls_published`` are both here because they are
    different numbers and the difference matters: the graph carries 133
    ``ceterms:subjectWebpage`` values, and most of them are the same sort-table
    address, so a check that made one request per distinct URL made far fewer than
    133 requests. Publishing only the larger number would overstate what a run did.
    """
    references = commission_references(document)
    urls = sorted(set(references))
    if verdicts is None:
        return {
            "state": NOT_CHECKED,
            "note": NOT_CHECKED_NOTE,
            "references_published": len(references),
            "urls_published": len(urls),
        }
    by_url = verdicts.by_url()
    covered = coverage_of(document, verdicts)
    return {
        "state": RECORDED,
        # The date the file was written, which is what it is and not when anything
        # was observed. `observed_first`/`observed_last` are the observation window,
        # and they can be months earlier: the checker carries a verdict forward
        # until it expires, so a run that requested nothing still restamps this.
        "checked": verdicts.checked,
        "observed_first": covered.first,
        "observed_last": covered.last,
        "note": page_note(document, verdicts),
        "references_published": len(references),
        "urls_published": len(urls),
        "urls_with_a_verdict": sum(1 for url in urls if url in by_url),
        # A URL the graph publishes and the run never reached is not covered by any
        # of the five verdicts, and rolling it into `alive` or `indeterminate` would
        # be inventing an observation. It gets its own count.
        "urls_without_a_verdict": sum(1 for url in urls if url not in by_url),
        # A verdict for a URL the graph no longer publishes is stale evidence. It is
        # reported rather than dropped, because a silently discarded row is how a
        # verdict file and a graph drift apart unnoticed.
        "verdicts_for_urls_no_longer_published": sum(
            1 for entry in verdicts.entries if entry.url not in set(urls)
        ),
        "verdicts": {name: covered.counts[name] for name in VERDICTS if covered.counts[name]},
    }


def page_note(document: Mapping[str, Any], verdicts: Verdicts | None) -> str:
    """The sentences for the page, always about a run and never about the Commission.

    Four shapes, because there are four things that can be true and only one of
    them used to have a sentence: no file at all, a file that covers nothing this
    graph publishes, observations from one day, and observations spread over the
    window a carried-forward verdict creates. The partial clause is appended to
    the last two rather than replacing them, since a run that covered thirteen of
    fourteen URLs did observe thirteen things and the reader wants both facts.
    """
    if verdicts is None:
        return NOT_CHECKED_NOTE
    covered = coverage_of(document, verdicts)
    if covered.covered == 0:
        return NOTHING_COVERED_NOTE.format(published=covered.published)
    template = RECORDED_NOTE if covered.one_day else RECORDED_SPAN_NOTE
    note = template.format(
        first=covered.first,
        last=covered.last,
        covered=covered.covered,
        published=covered.published,
        alive=covered.counts[ALIVE],
        redirected=covered.counts[REDIRECTED_ON_SITE] + covered.counts[REDIRECTED_OFF_SITE],
        unreachable=covered.counts[UNREACHABLE],
        indeterminate=covered.counts[INDETERMINATE],
    )
    if covered.uncovered:
        note += PARTIAL_NOTE.format(uncovered=covered.uncovered, published=covered.published)
    return note


def serialize(verdicts: Verdicts) -> str:
    """One canonical serialization, so a re-run produces a reviewable diff."""
    document = {
        "note": (
            "Observations from link-check runs, one row per distinct Commission URL. "
            "Each row states what one request from one machine at one time observed. "
            "No row is a statement about the Commission's site, and no verdict here "
            "changes any URL this project publishes."
        ),
        "checked": verdicts.checked,
        "verdicts": [
            {
                "url": entry.url,
                "verdict": entry.verdict,
                "checked": entry.checked,
                "status": entry.status,
                "final_url": entry.final_url,
                "title": entry.title,
            }
            for entry in sorted(verdicts.entries, key=lambda e: e.url)
        ],
    }
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"
