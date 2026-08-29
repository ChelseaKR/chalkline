# Contributing

Thanks for looking. A few things are specific to this repository.

## The rules that matter here

1. **Nothing is published to the Credential Registry.** Not production, not sandbox, not a
   single test record. This repository writes files to disk. Registry publication is not a
   contribution this project accepts.
2. **Model only what the source publishes.** If the Commission's page does not say it, it
   does not go in the graph. A property that would require a judgement call is left out and
   the omission is recorded in `PROVENANCE.md` with a reason. Absence is a valid answer.
3. **Check CTDL against the vendored schema, not against memory.** Every class and property
   is validated by `src/chalkline/ctdl/validate.py` before anything is written. If you need
   a term the schema does not admit, the schema is the authority.
4. **Never work around a site that declines automated access.** `scripts/fetch_sources.py`
   stops on an HTTP error. Do not add retries with different headers or user agents. If a
   page starts refusing, transcribe by hand and label the result as hand-transcribed.
5. **Counts are counted.** Every number in the docs and on the page is derived from the
   artifact it describes. Do not write a total into prose that nothing recomputes.

## Refreshing the sources

```bash
uv run python scripts/fetch_sources.py   # by hand, never in CI
```

Then update the `retrieved`, `bytes`, and `sha256` fields in each `.source.json` sidecar
(the script prints them), run `make build`, and review the diff. `tests/test_provenance.py`
fails if a sidecar and its artifact disagree.

New authorizations need CTIDs: `uv run chalkline mint-ctids`, then commit the ledger. Never
edit an existing CTID; an identifier that has been handed out does not change quietly.

## Before opening a pull request

```bash
make verify
```

That runs ruff, mypy strict, the test suite with a 97% coverage floor, and the check that
the committed `site/` matches a fresh build. All of it also runs in CI.

## Prose style

No em dashes. Do not characterize the Commission as deficient; the framing throughout is
that no machine-readable representation exists yet and this is what one could look like.
