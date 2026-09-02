"""The numbers in the prose are the numbers the build produces.

Everything the build writes is counted: ``site/coverage.json`` is derived from the emitted
graph, ``site/index.html`` counts the catalog at render time, and ``chalkline check`` holds
both byte-for-byte against a fresh build. The two documents a reader meets first, README.md
and PROVENANCE.md, retype those figures into markdown tables by hand, and nothing used to
check them. PROVENANCE.md even introduces its table with "Recomputed from the emitted graph
at build time", which was a description of where the numbers came from originally rather
than of anything that keeps them true.

One of them had already drifted: the README published 20 authorizations carrying
requirements or renewal terms, which is the two property counts added together with the
authorizations carrying both counted twice, where the graph and the page both say 13.

So every numeric row of both tables is bound to a freshly counted coverage statement here.
The binding is exhaustive in both directions: a row this module does not know about fails,
and a figure this module names that the table has stopped publishing fails too. Without that
pair, a row could be added to a table, or quietly deleted from one, and this file would go on
passing while checking less than it claims to.

The tables were the whole of it until 2026-08-27, and the opening sentence above was an
overclaim for that entire time. What was bound was two markdown tables; what the docstring
promised was the prose. README.md quotes at least sixteen more figures in ordinary sentences
around those tables, and every one of them could be edited to any value at all with the
suite still green: eight were changed at once to plainly wrong numbers and all 302 tests
passed. One of them was already wrong. The Status line said nineteen leaflets extend 22
authorizations "with descriptions, requirements, or renewal terms", where 22 is the number
linked to a leaflet and 18 is the number that carry anything read from one, the other four
being the authorizations whose leaflet page this project refuses to read.

The second half of this module binds that prose. CONTRIBUTING.md's rule is "counts are
counted: do not write a total into prose that nothing recomputes", and until now the prose
was the one place that rule was not enforced.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

import pytest

from chalkline import ctid as ctid_module
from chalkline.attachment import Attachment
from chalkline.ctdl import export
from chalkline.model import Catalog
from chalkline.sources import leaflets as leaflets_module

REPO_ROOT = Path(__file__).resolve().parents[1]

_ROW_RE = re.compile(r"^\|(?P<label>[^|]*)\|(?P<value>[^|]*)\|$")
_RULE_RE = re.compile(r":?-{2,}:?")
_COUNT_RE = re.compile(r"\d[\d,]*")


def documented(path: Path, heading: str) -> dict[str, str]:
    """Every ``| label | value |`` data row of the table under one heading, values as written.

    The value comes back unparsed on purpose. This used to capture ``[\\d,]+``, so a row the
    pattern could not read simply was not returned, and a figure written ``~9,999`` or
    ``about 9`` vanished from the comparison instead of failing it. Six labels appear in both
    tables, so the orphan check below still found them published and the whole thing stayed
    green while checking one row less. The row that cannot be read as a number is precisely
    the row that has to survive as far as an assertion.
    """
    text = path.read_text(encoding="utf-8")
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    lines = text[start : end if end != -1 else len(text)].splitlines()

    cells = [
        (match.group("label").strip(), match.group("value").strip())
        for line in lines
        if (match := _ROW_RE.fullmatch(line.strip()))
    ]
    rows: dict[str, str] = {}
    for index, (label, value) in enumerate(cells):
        following = cells[index + 1][1] if index + 1 < len(cells) else ""
        if _RULE_RE.fullmatch(value) or _RULE_RE.fullmatch(following):
            continue  # the rule itself, and the header row sitting on top of it
        rows[label] = value
    return rows


def figures(statement: dict[str, Any]) -> dict[str, int]:
    """Every figure the two tables are allowed to quote, keyed by how they label it."""
    authorizations = statement["authorizations"]
    entities = statement["entities"]
    properties = statement["license_properties"]
    leaflets = statement["leaflets"]
    return {
        "Rows published in the sort table": statement["source"]["rows_published"],
        "Authorizations in those rows": authorizations["published_in_source"],
        "Modeled as `ceterms:License`": entities["ceterms:License"],
        "Excluded, each with a recorded reason": authorizations["excluded"],
        "Excluded, with reasons below": authorizations["excluded"],
        "Subject alignments emitted": entities["ceterms:CredentialAlignmentObject"],
        "`ceterms:CredentialAlignmentObject` subject alignments emitted": entities[
            "ceterms:CredentialAlignmentObject"
        ],
        "Of those, supplied by following a published cross-reference": authorizations[
            "subject_alignments_from_a_cross_reference"
        ],
        "Authorizations whose scope was resolved by cross-reference": authorizations[
            "scope_resolved_by_cross_reference"
        ],
        "Authorizations with subject codes": authorizations["with_subject_codes"],
        "Authorizations the Commission publishes as `NONE` (not subject-coded)": authorizations[
            "published_as_not_subject_coded"
        ],
        "Authorizations carrying `ceterms:description`": properties["ceterms:description"],
        "Of those, described in a Commission leaflet": leaflets[
            "authorizations_with_leaflet_prose"
        ],
        "Authorizations carrying `ceterms:requires`": properties["ceterms:requires"],
        "Authorizations carrying `ceterms:renewal`": properties["ceterms:renewal"],
        "Authorizations carrying requirements or renewal terms": authorizations[
            "with_requirements_or_renewal_terms"
        ],
        "`ceterms:ConditionProfile` nodes emitted": entities["ceterms:ConditionProfile"],
        "Authorizations linked to a CTC leaflet": leaflets["authorizations_with_a_leaflet"],
        "Of those, carrying requirements the leaflet states for their own variant": leaflets[
            "authorizations_with_variant_requirements"
        ],
        "Leaflet pages read": leaflets["leaflet_pages_read"],
        "Leaflet pages refused on identity": leaflets["leaflet_pages_refused"],
        "Leaflet pages vendored": leaflets["leaflet_pages_vendored"],
        "Of those, retrieved and attached to nothing": leaflets[
            "leaflet_pages_vendored_and_attached_to_nothing"
        ],
        "Leaflets in the Commission's index": leaflets["leaflets_in_the_commission_index"],
        "Index rows redirecting a retired document code": leaflets[
            "index_rows_redirecting_a_retired_document_code"
        ],
        "CTIDs in the ledger (133 licenses plus the Commission)": len(ctid_module.load_ledger()),
    }


TABLES = (
    (REPO_ROOT / "README.md", "## What this is"),
    (REPO_ROOT / "PROVENANCE.md", "## What is counted"),
)


@pytest.fixture(scope="module")
def statement(
    real_catalog: Catalog,
    real_attachments: dict[str, Attachment],
    real_index: leaflets_module.Index,
    vendored_pages: tuple[str, ...],
) -> dict[str, object]:
    document = export.project_graph(real_catalog, ctid_module.load_ledger(), real_attachments)
    return export.coverage(document, real_catalog, real_attachments, real_index, vendored_pages)


def _id(value: Path | str) -> str:
    return value.name if isinstance(value, Path) else value.removeprefix("## ")


@pytest.mark.parametrize(("path", "heading"), TABLES, ids=_id)
def test_every_documented_count_is_the_count_the_build_produces(
    path: Path, heading: str, statement: dict[str, Any]
) -> None:
    known = figures(statement)
    rows = documented(path, heading)
    assert rows, f"{path.name} publishes no counted table under {heading!r}"
    unknown = sorted(set(rows) - set(known))
    assert unknown == [], (
        f"{path.name} publishes figures nothing checks: {unknown}. Add each one to "
        "figures() with the coverage-statement value it quotes, or it can drift."
    )
    unreadable = {label: value for label, value in rows.items() if not _COUNT_RE.fullmatch(value)}
    assert unreadable == {}, (
        f"{path.name} publishes figures that are not numbers: {unreadable}. A row this "
        "cannot read is a row it cannot check, so it fails here rather than being skipped."
    )
    wrong = {
        label: (value, known[label])
        for label, value in rows.items()
        if int(value.replace(",", "")) != known[label]
    }
    assert wrong == {}, f"{path.name} says (documented, built): {wrong}"


def test_every_figure_this_module_binds_is_still_published(statement: dict[str, Any]) -> None:
    """A label that has left both tables is a check that has stopped checking anything."""
    published = {label for path, heading in TABLES for label in documented(path, heading)}
    orphaned = sorted(set(figures(statement)) - published)
    assert orphaned == [], (
        f"figures() names rows no table publishes any more: {orphaned}. Drop them, or the "
        "count of things checked here is smaller than it looks."
    )


# --- The prose around those tables, which quoted the build and nothing recomputed ----------

PROSE_NOUNS = (
    "authorizations",
    "leaflets",
    "credential leaflets",
    "leaflet pages",
    "entities",
    "subject alignments",
    "rows",
    "references",
    "exclusions",
    "findings",
)
"""The plural nouns that make a figure beside them a claim about what the build produced.

This is the scan's denominator and it is stated rather than implied. Singular phrasing is
out of scope on purpose: "exactly one leaflet" and "one apparent gap" are prose about a
particular thing, not totals, and a scan that treated them as totals would spend its
failures on sentences no build number can move.
"""

NUMBER_WORDS: Final = {
    word: value
    for value, word in enumerate(
        (
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
            "twenty",
        )
    )
}
"""The README spells small figures as words. A check that read only digits would have
skipped "Ten leaflet pages were read; eighteen authorizations carry prose from one", which
is four figures and two of the leaflet totals a reader meets."""

_FIGURE_TOKEN = re.compile(
    rf"(?<![\w.-])(?:[0-9][0-9,]*|{'|'.join(NUMBER_WORDS)})(?![\w.-])", re.IGNORECASE
)
"""One figure as the README writes it. The lookarounds keep version strings (`0.16.4`),
dates (`2026-08-07`) and leaflet codes (`CL-902`) out: each of those is a figure glued to a
dot, a dash or a word, and none of them is a count of anything the build emits.

That exclusion is right and stays. It did mean the pinned tool floors were the one class of
figure in the README that nothing read at all, and they had drifted a release behind the
pins. `tests/test_documented_floors.py` reads those out of `pyproject.toml` instead, which is
where they come from; loosening this pattern to reach them would only have made a count check
into a worse version-string check."""


def as_int(token: str) -> int:
    """The value of a figure the README wrote as digits or as an English word."""
    lowered = token.lower()
    if lowered in NUMBER_WORDS:
        return NUMBER_WORDS[lowered]
    return int(token.replace(",", ""))


def prose(path: Path) -> str:
    """The document's prose: no fenced code, no table rows, whitespace collapsed.

    Table rows come out because they are already bound, row by row, by the tests above. Code
    fences come out because a figure in a shell transcript is a command, not a claim.
    """
    text = re.sub(r"```.*?```", " ", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    kept = [line for line in text.splitlines() if not line.lstrip().startswith("|")]
    return " ".join(" ".join(kept).split())


def prose_figures(statement: dict[str, Any], findings: int) -> dict[str, int]:
    """Every figure the README's prose is allowed to quote, keyed by what it means.

    ``findings`` comes from the committed ``site/ctdl-validate.json``, which
    ``tests/test_ctdl_validate_evidence.py`` already re-runs the validator against, so this
    reads a file another test holds to a fresh run rather than trusting it on its own.
    """
    authorizations = statement["authorizations"]
    entities = statement["entities"]
    leaflets = statement["leaflets"]
    reasons = statement["excluded_by_reason"]
    return {
        "modeled": entities["ceterms:License"],
        "graph entities": entities["ceterms:License"] + entities["ceterms:CredentialOrganization"],
        "excluded": authorizations["excluded"],
        "excluded because the document indicates the subjects": excluded_for(
            reasons, "indicated on the issued document"
        ),
        "excluded because nothing describes the scope": excluded_for(
            reasons, "no subject code, no subject, and no note"
        ),
        "scope resolved by cross-reference": authorizations["scope_resolved_by_cross_reference"],
        "subject alignments from a cross-reference": authorizations[
            "subject_alignments_from_a_cross_reference"
        ],
        # What the modeled count was before the eight cross-references were followed. The
        # README tells that as a before-and-after, so the "before" has to be derived from the
        # same statement as the "after" or half the sentence goes unchecked.
        "modeled before cross-references were followed": (
            authorizations["modeled"] - authorizations["scope_resolved_by_cross_reference"]
        ),
        "leaflet pages vendored": leaflets["leaflet_pages_vendored"],
        "leaflet pages vendored and attached to nothing": leaflets[
            "leaflet_pages_vendored_and_attached_to_nothing"
        ],
        "leaflet pages read": leaflets["leaflet_pages_read"],
        "leaflet pages refused": leaflets["leaflet_pages_refused"],
        "authorizations with a leaflet": leaflets["authorizations_with_a_leaflet"],
        "authorizations with leaflet prose": leaflets["authorizations_with_leaflet_prose"],
        "authorizations with requirements or renewal terms": authorizations[
            "with_requirements_or_renewal_terms"
        ],
        "authorizations with variant requirements": leaflets[
            "authorizations_with_variant_requirements"
        ],
        "authorizations whose variant no heading states": sum(
            leaflets["variant_qualifiers_no_heading_states"].values()
        ),
        "authorizations matched against the leaflet page's own title": leaflets[
            "matched_against_a_string_published_by"
        ]["the leaflet page's own title"],
        "ctdl-validate findings": findings,
    }


def excluded_for(reasons: dict[str, int], fragment: str) -> int:
    """The exclusion count whose published reason contains ``fragment``, and only that one.

    The keys of ``excluded_by_reason`` are the Commission-facing sentences themselves, so a
    fragment is how a test names one. A fragment that matched two reasons, or none, would
    quietly return a number about the wrong thing, so it raises instead.
    """
    matched = [reason for reason in reasons if fragment in reason]
    if len(matched) != 1:
        raise AssertionError(
            f"{fragment!r} identifies {len(matched)} of the {len(reasons)} published "
            "exclusion reasons; it has to identify exactly one"
        )
    return reasons[matched[0]]


CLAIMS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    (
        r"([\w,]+) authorizations are modeled, tested, and published as JSON-LD; "
        r"([\w,]+) of them are linked to one of the ([\w,]+) vendored credential leaflets, "
        r"([\w,]+) carry a description read from one, and ([\w,]+) carry requirements or "
        r"renewal terms\.",
        (
            "modeled",
            "authorizations with a leaflet",
            "leaflet pages vendored",
            "authorizations with leaflet prose",
            "authorizations with requirements or renewal terms",
        ),
    ),
    (r"and ([\w,]+) of its credential leaflets, retrieved", ("leaflet pages vendored",)),
    (
        r"Today it reports `([\w,]+) findings` on all ([\w,]+) entities",
        ("ctdl-validate findings", "graph entities"),
    ),
    (
        r"took the modeled count from ([\w,]+) to ([\w,]+) and added ([\w,]+) subject alignments",
        (
            "modeled before cross-references were followed",
            "modeled",
            "subject alignments from a cross-reference",
        ),
    ),
    (
        r"([\w,]+) rows in the third case carry a Commission note",
        ("scope resolved by cross-reference",),
    ),
    (r"All ([\w,]+) references were followed", ("scope resolved by cross-reference",)),
    (r"the ([\w,]+) exclusions left", ("excluded",)),
    (
        r"([\w,]+) authorizations remain unmodeled: ([\w,]+) publish \"Indicated on Document\" "
        r"and ([\w,]+) publishes nothing at all",
        (
            "excluded",
            "excluded because the document indicates the subjects",
            "excluded because nothing describes the scope",
        ),
    ),
    (
        r"Only ([\w,]+) of the ([\w,]+) authorizations have a Commission leaflet attached",
        ("authorizations with a leaflet", "modeled"),
    ),
    (
        r"the family base of the ([\w,]+) authorizations the sort table publishes",
        ("authorizations matched against the leaflet page's own title",),
    ),
    (
        r"([\w,]+) leaflets fail that, for opposite reasons",
        ("leaflet pages refused",),
    ),
    (
        r"([\w,]+) leaflet pages were read; ([\w,]+) authorizations carry prose from one",
        ("leaflet pages read", "authorizations with leaflet prose"),
    ),
    (
        r"([\w,]+) authorizations gain their own variant's requirements this way\. "
        r"([\w,]+) do not",
        (
            "authorizations with variant requirements",
            "authorizations whose variant no heading states",
        ),
    ),
    (
        r"([\w,]+) leaflet pages are vendored and ([\w,]+) of them are attached to nothing",
        ("leaflet pages vendored", "leaflet pages vendored and attached to nothing"),
    ),
    (
        r"Each of those ([\w,]+) was retrieved",
        ("leaflet pages vendored and attached to nothing",),
    ),
)
"""Every sentence of README prose that quotes a figure the build counts.

Each pattern captures its figures in order and names the statement value each one has to
equal. The patterns are deliberately long: a claim has to match the sentence, so rewording
the sentence around the number fails here instead of leaving the number unchecked.
"""

NOT_A_BUILD_FIGURE: Final = (
    (
        "Two leaflets that a near-miss title suggested were deliberately",
        "a count of documents that were never retrieved. The coverage statement counts what "
        "was fetched and what it matched; a deliberate non-retrieval leaves no artifact to "
        "count, and PROVENANCE.md names both leaflets instead.",
    ),
)
"""Figures the scan below finds beside a counted noun that the build does not produce.

Listed with the reason, one by one, rather than by loosening the scan: an exemption a reader
can see is a different thing from a pattern that never looked.
"""


@pytest.fixture(scope="module")
def findings() -> int:
    """How many findings the committed independent-validator report holds."""
    report = json.loads((REPO_ROOT / "site" / "ctdl-validate.json").read_text(encoding="utf-8"))
    return len(report["findings"])


def claim_spans(text: str) -> list[tuple[int, int]]:
    """Where each claim matched, so the scan below can tell covered figures from loose ones."""
    return [span for pattern, _ in CLAIMS for span in [_only_match(text, pattern).span()]]


def _only_match(text: str, pattern: str) -> re.Match[str]:
    found = list(re.finditer(pattern, text))
    assert len(found) == 1, (
        f"the claim /{pattern}/ matches README.md {len(found)} times. A claim that matches "
        "nothing has stopped checking its sentence, and one that matches twice is checking "
        "an ambiguous one; both are failures, not skips."
    )
    return found[0]


def test_every_prose_claim_still_matches_its_sentence() -> None:
    """A reworded sentence fails here rather than dropping out of the comparison below."""
    assert claim_spans(prose(REPO_ROOT / "README.md"))


def test_every_figure_the_prose_quotes_is_the_figure_the_build_produces(
    statement: dict[str, Any], findings: int
) -> None:
    known = prose_figures(statement, findings)
    text = prose(REPO_ROOT / "README.md")
    wrong: dict[str, tuple[int, int]] = {}
    for pattern, keys in CLAIMS:
        match = _only_match(text, pattern)
        assert len(match.groups()) == len(keys), f"/{pattern}/ captures {len(match.groups())}"
        for token, key in zip(match.groups(), keys, strict=True):
            if as_int(token) != known[key]:
                wrong[f"{key} (in /{pattern[:40]}.../)"] = (as_int(token), known[key])
    assert wrong == {}, f"README.md prose says (documented, built): {wrong}"


def test_no_figure_in_the_prose_goes_unchecked(statement: dict[str, Any], findings: int) -> None:
    """The denominator. Every figure beside a counted noun is bound, or exempted by name.

    Without this, the claims above would check exactly the sentences somebody remembered to
    write down, and a new paragraph quoting a new total would sail past a suite whose whole
    subject is that totals are counted.
    """
    text = prose(REPO_ROOT / "README.md")
    spans = claim_spans(text)
    exempt = [fragment for fragment, _ in NOT_A_BUILD_FIGURE]
    for fragment in exempt:
        assert fragment in text, f"NOT_A_BUILD_FIGURE names {fragment!r}, which README.md lost"

    loose: list[str] = []
    for match in _FIGURE_TOKEN.finditer(text):
        following = text[match.end() : match.end() + 60]
        if not any(
            re.match(rf"\s+(?:[\w']+\s+){{0,3}}{noun}\b", following) for noun in PROSE_NOUNS
        ):
            continue
        if any(start <= match.start() and match.end() <= end for start, end in spans):
            continue
        window = text[max(0, match.start() - 60) : match.end() + 60]
        if any(fragment in window for fragment in exempt):
            continue
        loose.append(f"{match.group(0)!r} in ...{window}...")
    assert loose == [], (
        "README.md prose quotes figures nothing recomputes:\n"
        + "\n".join(loose)
        + "\nAdd a CLAIMS entry binding each to a coverage-statement figure, or name it in "
        "NOT_A_BUILD_FIGURE with the reason the build cannot produce it."
    )


@pytest.mark.parametrize(
    ("original", "doctored"),
    [
        ("133 authorizations are modeled", "134 authorizations are modeled"),
        ("Ten leaflet pages were read", "Nine leaflet pages were read"),
        ("all 134 entities", "all 135 entities"),
        ("added 538 subject alignments", "added 539 subject alignments"),
    ],
)
def test_a_doctored_figure_is_caught(
    statement: dict[str, Any], findings: int, original: str, doctored: str
) -> None:
    """The control. Each of these edits is one the check has to reject, so it is made here.

    The README on disk is not touched: the same claims are run over a doctored copy of its
    prose, which is the only way to show that a passing run above is a statement about the
    figures and not about the check being unable to fail.
    """
    known = prose_figures(statement, findings)
    text = prose(REPO_ROOT / "README.md")
    assert original in text, f"README.md no longer says {original!r}"
    doctored_text = text.replace(original, doctored)

    caught = False
    for pattern, keys in CLAIMS:
        found = list(re.finditer(pattern, doctored_text))
        if len(found) != 1:
            caught = True
            continue
        caught = caught or any(
            as_int(token) != known[key] for token, key in zip(found[0].groups(), keys, strict=True)
        )
    assert caught, f"changing {original!r} to {doctored!r} left every claim satisfied"
