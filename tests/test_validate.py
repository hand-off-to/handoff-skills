import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import validate  # noqa: E402

SCHEMA = json.loads(
    (Path(__file__).resolve().parent.parent / "schema" / "skill.schema.json").read_text()
)

VALID_SKILL = {
    "key": "grounded",
    "version": 1,
    "name": "Grounded",
    "status": "active",
    "definition": {
        "instructions": "Answer only from provided context.",
        "doc_url": "https://example.com/docs",
    },
}


def test_valid_skill_manifest_passes():
    assert validate.validate_data(SCHEMA, VALID_SKILL) == []


def test_missing_instructions_fails():
    bad = {**VALID_SKILL, "definition": {"doc_url": "https://example.com/docs"}}
    assert validate.validate_data(SCHEMA, bad)


def test_missing_doc_url_fails():
    bad = {**VALID_SKILL, "definition": {"instructions": "Hi."}}
    assert validate.validate_data(SCHEMA, bad)


def test_bad_key_pattern_fails():
    bad = {**VALID_SKILL, "key": "Grounded Skill"}
    assert validate.validate_data(SCHEMA, bad)


def test_non_http_doc_url_fails():
    bad = {
        **VALID_SKILL,
        "definition": {**VALID_SKILL["definition"], "doc_url": "javascript:alert(1)"},
    }
    assert validate.validate_data(SCHEMA, bad)


def test_catalog_mismatch_version_reported():
    catalog = {"skills": [{"key": "grounded", "version": 2, "path": "skills/grounded.yaml"}]}
    manifests = [("skills/grounded.yaml", VALID_SKILL)]  # version 1
    errs = validate.catalog_errors(catalog, manifests)
    assert any("version" in e for e in errs)


def test_catalog_missing_entry_reported():
    catalog = {"skills": []}
    manifests = [("skills/grounded.yaml", VALID_SKILL)]
    errs = validate.catalog_errors(catalog, manifests)
    assert any("grounded" in e for e in errs)


def test_catalog_orphan_entry_reported():
    catalog = {"skills": [{"key": "ghost", "version": 1, "path": "skills/ghost.yaml"}]}
    errs = validate.catalog_errors(catalog, [])
    assert any("ghost" in e for e in errs)


def test_valid_svg_passes():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h24v24H0z"/></svg>'
    assert validate.svg_errors(svg) == []


def test_svg_with_script_rejected():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert any("script" in e for e in validate.svg_errors(svg))


def test_svg_with_event_handler_rejected():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect onload="x()"/></svg>'
    assert any("event-handler" in e for e in validate.svg_errors(svg))


def test_svg_malformed_rejected():
    assert any("well-formed" in e for e in validate.svg_errors("<svg><path></svg>"))


def test_svg_non_svg_root_rejected():
    assert any("root element" in e for e in validate.svg_errors("<html></html>"))


def test_svg_with_entity_dtd_rejected():
    svg = '<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY x "y">]><svg xmlns="http://www.w3.org/2000/svg"/>'
    assert validate.svg_errors(svg)


def test_orphan_icon_reported(tmp_path):
    icon = tmp_path / "ghost.svg"
    icon.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    errs = validate.icon_errors([icon])
    assert any("no matching manifest" in e for e in errs)


def test_repo_is_valid_end_to_end():
    assert validate.main() == 0
