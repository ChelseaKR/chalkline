# The `@id` host: what it should be, and who decides

Every node in `site/credentials.jsonld` that carries a CTID also carries an `@id` under
`https://chalkline.chelseakr.com/ctdl/resources/`. **That host does not resolve.** Nothing has
been registered, deployed, or published, and nothing in this document does any of those
things. It sets out what an `@id` is for, what the unresolved host actually costs, the three
options, and a recommendation. Choosing among them is the repository owner's call, because
two of the three amount to publishing.

## What is checkable here, and what is not

This repository's habit is to check claims against a vendored artifact. Two of the claims
below can be:

- **The context makes `@id` an IRI, not a label.** `src/chalkline/ctdl/ctdl-context.json`
  declares no `@vocab` and no `@base`, and types properties like `ceterms:subjectWebpage` and
  `ceterms:sameAs` as `"@type": "@id"`. A JSON-LD processor reading this document will treat
  every `@id` as an absolute IRI naming a resource.
- **`ceterms:ctid` is a string, and it is not the `@id`.** The context types it `xsd:string`,
  and the schema defines it as the identifier "by which the creator, owner or provider of a
  resource recognizes it in transactions with the external environment". It is a name the
  publisher holds; it is not a location.

What is **not** checkable from anything vendored here is the Credential Registry's own
behaviour on ingest: what it does to an `@id` a publisher submits, and what URI it serves a
hosted record under. That behaviour is documented on credreg.net and observable in the
Registry itself, and this repository has fetched neither. The paragraphs below that describe
it are stated from Credential Engine's published documentation and are marked as such. If this
decision is ever taken to Credential Engine, that is the first thing to confirm with them
rather than with this document.

## What linked-data practice expects

The four Linked Data principles are: use URIs as names for things; use HTTP URIs so people
can look them up; when someone looks one up, provide useful information using the standards;
and include links to other URIs. The third is the one at issue. An HTTP `@id` that returns
nothing is not *invalid* RDF, and no validator will reject it. It is a name that keeps the
promise the scheme makes, `http`, without keeping it.

Two things follow, and it is worth keeping them apart:

- **Correctness.** Unaffected. The graph merges, the CTIDs are unique and spec-conformant, the
  classes and properties validate against the vendored schema encoding, and every statement
  in the document is true whether or not the host answers.
- **Usefulness and credibility.** Affected. A reader who dereferences an `@id` expects a
  description of the thing. Getting nothing reads as unfinished, and for a project whose whole
  argument is discipline about what it asserts, that impression costs more than it would for
  most projects.

## What Credential Engine does with `@id` and CTID

*From Credential Engine's published documentation, not from an artifact vendored here.*

The Registry is the identity authority for the records it holds. A resource in the Registry is
identified by its CTID, and the Registry serves it under a registry URI built from that CTID.
A publisher does not get to keep its own `@id` as the canonical identifier for a record the
Registry hosts; the registry URI is what other records link to, and it resolves, because the
Registry serves it.

Two consequences matter for this repository:

1. **The unresolved host is not a barrier to publishing.** If these records were ever
   published, the Registry's URI would become the identifier that resolves. The `@id` here is
   a pre-publication placeholder for records that are deliberately not published.
2. **The CTIDs are already doing their job.** They are spec-conformant, ledger-stable, and
   the thing a registry would key on. `src/chalkline/ctid.py` argues this at length: a
   publisher can hold stable identifiers for its own inventory before it publishes, which is
   the position the Commission would be in. That argument does not depend on a host.

The human-facing side is separately in good shape. `ceterms:subjectWebpage` is defined as the
"Webpage that describes this entity", it is emitted on all 133 licenses and on the
organization, and every one of those URLs is on `www.ctc.ca.gov`. The page a person would want
already resolves, and it resolves to the Commission rather than to this project, which is the
right answer for a project that models someone else's credentials.

## What actually breaks today

Counted, not asserted:

- **134 `@id` values do not dereference** (133 licenses and one organization). Nested profiles
  carry no `@id` at all, so they are not affected.
- **The host appears in one other place: `ceterms:ownedBy`.** Every one of the 133 licences
  names the organization by its `@id`, so the host is emitted 267 times, not 134. That is an
  internal node reference rather than a second external dependency, and it does not
  dereference for the same reason the `@id` values do not. Every value pointing *outward*
  goes to ctc.ca.gov: `ceterms:subjectWebpage` on all 134 entities, and the framework and
  leaflet links beneath them. The browsable page in `site/` uses relative links and does not
  mention the host at all.
- **Nothing in the build depends on the host resolving.** No test fetches it, no validation
  requires it, and `chalkline check` is unaffected.

So the cost is entirely one of impression and of the fourth linked-data principle. It is real,
and it is bounded.

## The options

### 1. Leave it unresolved, and say so in the document

Add a note to the graph and the README that the `@id` namespace is a pre-publication
identifier for records deliberately not published, and that the resolving description of each
credential is the `ceterms:subjectWebpage` on ctc.ca.gov.

- **For.** No infrastructure, no cost, no domain to keep renewed, and nothing published. It is
  the honest state of affairs: these records are not published, so their identifiers do not
  resolve, and pretending otherwise would be the thing this project keeps refusing to do.
- **Against.** A reader has to read the note to know it is deliberate. Without one it looks
  like an oversight, and an oversight is exactly what a reviewer of this project is scanning
  for.

### 2. Point the host at a static site

Publish `site/` at the host, so `https://chalkline.chelseakr.com/ctdl/resources/ce-…` returns
something about that credential.

- **For.** Keeps the linked-data promise. It is a small amount of work: the artifacts are
  already generated, already deterministic, and already self-contained.
- **Against.** It is publishing. A public page of California credential data, unofficial but
  looking authoritative to anyone who lands on it mid-scroll, is a different act from a
  private repository, and it is not this project's to decide. It also adds a standing
  obligation: a DNS name to keep, a host to keep serving, and stale data to keep an eye on,
  because an `@id` that resolves to a page describing an authorization the Commission has
  since changed is worse than one that resolves to nothing. And it needs a per-CTID route to
  be worth doing at all; publishing only the index page would leave all 134 `@id` values still
  dereferencing to nothing.

### 3. A different identifier scheme

Two variants worth naming and neither worth taking:

- **A URN or `tag:` URI**, for example `urn:uuid:…`. Honest about not being dereferenceable,
  since neither scheme promises to be. But it loses the ability to become an HTTP URI later
  without rewriting every `@id`, and CTDL's own ecosystem is HTTP-shaped throughout.
- **A registry-shaped URI** under `credentialengineregistry.org`. Rejected outright, and there
  is a test asserting it. Those URIs would imply these records exist in the Credential
  Registry. They do not, and a URI that resolves to someone else's 404 is a worse claim than
  one that resolves to nothing.

There is also a fourth idea that sounds appealing and is wrong: dropping `@id` altogether and
leaving the nodes blank. That would make the licenses blank nodes, which cannot be referred to
from outside the document, and it would throw away the one thing the CTID ledger exists to
demonstrate.

## Recommendation

**Take option 1 now, and hold option 2 for the moment the owner decides to publish.**

The reason is that the host resolving and the records being published are the same decision,
not two. An `@id` that resolves is a page that exists, and a page that exists is publication.
This project has been careful throughout not to publish anything to anyone's registry and not
to imply the Commission has endorsed it, and quietly standing up a domain so that a URI stops
404ing would be publication arrived at through a technical side door rather than chosen. The
cost of waiting is one line of documentation; the cost of not waiting is a decision made by
default.

Concretely, if option 1 is taken: keep `RESOURCE_BASE` as it is, note in `PROVENANCE.md` and in
the graph's own `comment` that the namespace is a pre-publication identifier and that the
resolving description of each credential is its `ceterms:subjectWebpage` on ctc.ca.gov, and
leave the test that keeps `credentialengineregistry.org` out of `@id` exactly where it is.

If option 2 is later chosen, three things should come with it, and none of them is
retrofittable cheaply afterwards:

1. **Per-CTID routes.** `…/ctdl/resources/<ctid>` must return a description of that credential,
   not a redirect to the index. Content negotiation to JSON-LD would be better still.
2. **The unofficial statement above the fold on every route**, in the same words the graph and
   the page already carry.
3. **A visible retrieval date on every page**, so a reader can see how old the underlying
   Commission data is without opening the coverage statement.

Until then the identifiers are names, held stably, for records nobody has published. That is a
defensible thing for them to be, and it is worth saying out loud rather than leaving a reader
to discover a 404.
