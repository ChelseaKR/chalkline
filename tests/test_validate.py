"""The validator is the mechanism behind every modeling claim, so it is tested on failures.

Each test here is a mistake somebody could plausibly make while modeling onto CTDL. If the
validator misses one of these, the export's docstrings become assertions nothing checks.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from chalkline.ctdl import validate

SCHEMA = validate.load_schema()
CONTEXT = validate.load_context()


def findings(*entities: Mapping[str, object]) -> list[str]:
    return validate.validate({"@graph": list(entities)}, SCHEMA, CONTEXT)


def valid_license() -> dict[str, object]:
    return {
        "@type": "ceterms:License",
        "ceterms:name": {"en-US": "A credential"},
        "ceterms:subjectWebpage": "https://example.gov/",
    }


def test_a_well_formed_entity_produces_no_findings() -> None:
    assert findings(valid_license()) == []


def test_an_invented_class_is_caught() -> None:
    (finding,) = findings({"@type": "ceterms:TeachingCredential"})
    assert "not an rdfs:Class" in finding


def test_an_invented_property_is_caught() -> None:
    entity = valid_license() | {"ceterms:gradeSpan": "K-12"}
    assert any("not a term in the CTDL schema" in f for f in findings(entity))


def test_a_property_used_outside_its_domain_is_caught() -> None:
    """The mistake this project actually had to avoid: codedNotation is not on a License."""
    entity = valid_license() | {"ceterms:codedNotation": "R1S"}
    assert any("not in the domain of ceterms:License" in f for f in findings(entity))


def test_a_language_map_written_as_a_bare_string_is_caught() -> None:
    entity = valid_license() | {"ceterms:name": "A credential"}
    assert any("language map" in f for f in findings(entity))


def test_a_language_map_holding_a_non_string_is_caught() -> None:
    entity = valid_license() | {"ceterms:name": {"en-US": 7}}
    assert any("string or a non-empty list of strings" in f for f in findings(entity))


def test_a_language_map_may_hold_a_list_of_strings() -> None:
    """CTDL writes a repeated single-value property once per value under one language tag."""
    entity = valid_license() | {
        "ceterms:requires": [
            {
                "@type": "ceterms:ConditionProfile",
                "ceterms:name": {"en-US": "Requirements"},
                "ceterms:condition": {"en-US": ["Hold a degree.", "Pass an exam."]},
            }
        ]
    }
    assert findings(entity) == []


def test_an_empty_list_in_a_language_map_is_caught() -> None:
    """An empty list says nothing, and a property that says nothing should not be emitted."""
    entity = valid_license() | {"ceterms:name": {"en-US": []}}
    assert any("string or a non-empty list of strings" in f for f in findings(entity))


def test_a_language_map_holding_a_list_with_a_non_string_is_caught() -> None:
    entity = valid_license() | {"ceterms:name": {"en-US": ["ok", 7]}}
    assert any("string or a non-empty list of strings" in f for f in findings(entity))


def test_a_literal_where_a_language_map_belongs_is_caught() -> None:
    """postalCode takes xsd:string, and the address lines around it do not."""
    entity = {
        "@type": "ceterms:Place",
        "ceterms:postalCode": {"en-US": "95811"},
    }
    assert any("ceterms:postalCode" in f for f in findings(entity))


def test_a_nested_node_of_the_wrong_class_is_caught() -> None:
    entity = valid_license() | {
        "ceterms:regulatedIn": [{"@type": "ceterms:Place", "ceterms:name": {"en-US": "CA"}}]
    }
    assert any("its range is" in f for f in findings(entity))


def test_a_nested_node_is_itself_validated() -> None:
    entity = valid_license() | {
        "ceterms:regulatedIn": [
            {"@type": "ceterms:JurisdictionProfile", "ceterms:codedNotation": "CA"}
        ]
    }
    assert any("not in the domain of ceterms:JurisdictionProfile" in f for f in findings(entity))


def test_a_wrong_literal_shape_is_caught() -> None:
    entity = valid_license() | {"ceterms:subjectWebpage": 12}
    assert any("its range is" in f for f in findings(entity))


def test_an_iri_reference_is_accepted_where_a_class_is_expected() -> None:
    entity = valid_license() | {"ceterms:ownedBy": ["https://example.org/org/1"]}
    assert findings(entity) == []


def test_a_node_without_a_type_is_caught() -> None:
    assert any("no @type" in f for f in findings({"ceterms:name": {"en-US": "x"}}))


def test_a_list_of_types_is_refused() -> None:
    entity = {"@type": ["ceterms:License", "ceterms:Certification"]}
    assert any("not a single class name" in f for f in findings(entity))


def test_a_non_object_graph_member_is_caught() -> None:
    assert any("not an object" in f for f in validate.validate({"@graph": ["x"]}, SCHEMA, CONTEXT))


def test_an_empty_graph_is_caught() -> None:
    assert validate.validate({"@graph": []}, SCHEMA, CONTEXT) == ["document has an empty @graph"]


def test_check_raises_and_summarizes() -> None:
    document = {"@graph": [{"@type": "ceterms:NotAClass"}]}
    with pytest.raises(ValueError, match="does not validate against CTDL"):
        validate.check(document, SCHEMA, CONTEXT)


def test_check_truncates_a_long_finding_list() -> None:
    document = {"@graph": [{"@type": f"ceterms:NotAClass{n}"} for n in range(15)]}
    with pytest.raises(ValueError, match="and 5 more"):
        validate.check(document, SCHEMA, CONTEXT)


def test_the_vendored_schema_defines_the_classes_this_project_relies_on() -> None:
    for name in (
        "ceterms:License",
        "ceterms:CredentialOrganization",
        "ceterms:CredentialAlignmentObject",
        "ceterms:JurisdictionProfile",
        "ceterms:IdentifierValue",
        "ceterms:Place",
    ):
        assert SCHEMA[name]["@type"] == "rdfs:Class"


def test_license_is_a_credential_subclass() -> None:
    assert "ceterms:Credential" in SCHEMA["ceterms:License"]["rdfs:subClassOf"]


def test_a_class_used_where_a_property_belongs_is_caught() -> None:
    """``ceterms:License`` is a class; naming it as a property is a different mistake."""
    entity = valid_license() | {"ceterms:License": "x"}
    assert any("not an rdf:Property" in f for f in findings(entity))


def test_a_property_absent_from_the_vendored_context_is_caught() -> None:
    """The schema and the context are separate artifacts, and both have to admit a term."""
    trimmed = {term: value for term, value in CONTEXT.items() if term != "ceterms:subjectWebpage"}
    reported = validate.validate({"@graph": [valid_license()]}, SCHEMA, trimmed)
    assert any("not declared in the CTDL JSON-LD context" in f for f in reported)


def test_a_property_with_no_declared_range_is_not_range_checked() -> None:
    """``meta:`` terms carry no rangeIncludes; the range check has nothing to say about them."""
    definition = {"@type": "rdf:Property", "schema:domainIncludes": ["ceterms:License"]}
    schema = dict(SCHEMA) | {"ceterms:madeUp": definition}
    context = dict(CONTEXT) | {"ceterms:madeUp": {"@type": "xsd:string"}}
    entity = valid_license() | {"ceterms:madeUp": object()}
    assert validate.validate({"@graph": [entity]}, schema, context) == []
