#!/usr/bin/env python3
"""Validate skill manifests against the JSON Schema and the catalog index."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from xml.parsers.expat import ExpatError

import yaml
from defusedxml import minidom
from defusedxml.common import DefusedXmlException
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "skill.schema.json"
SKILLS_DIR = ROOT / "skills"
CATALOG_PATH = ROOT / "catalog.yaml"

# Sidecar SVG icons are rendered in the browser, so reject anything that could
# carry active content even though manifests come from a reviewed repo.
_SCRIPT_RE = re.compile(r"<\s*script\b", re.IGNORECASE)
_HANDLER_RE = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def load_yaml(path: Path) -> dict:
    with path.open() as fh:
        return yaml.safe_load(fh)


def manifest_paths() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.rglob("*.yaml"))


def icon_paths() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.rglob("*.svg"))


def validate_data(schema: dict, data: dict) -> list[str]:
    validator = Draft202012Validator(schema)
    return [err.message for err in sorted(validator.iter_errors(data), key=str)]


def svg_errors(content: str) -> list[str]:
    """Validate a sidecar SVG: well-formed XML, an <svg> root, no active content."""
    errors: list[str] = []
    if _SCRIPT_RE.search(content):
        errors.append("contains a <script> element")
    if _HANDLER_RE.search(content):
        errors.append("contains an on* event-handler attribute")
    try:
        dom = minidom.parseString(content)
    except DefusedXmlException:
        errors.append("uses disallowed XML features (entities/DTD)")
        return errors
    except (ExpatError, ValueError):
        errors.append("is not well-formed XML")
        return errors
    if dom.documentElement.localName != "svg":
        errors.append("root element is not <svg>")
    return errors


def icon_errors(icons: list[Path]) -> list[str]:
    """Each sidecar SVG must sit beside a manifest of the same name and be safe."""
    errors: list[str] = []
    for path in icons:
        try:
            rel = str(path.relative_to(ROOT))
        except ValueError:
            rel = path.name
        if not path.with_suffix(".yaml").exists():
            errors.append(f"{rel}: icon has no matching manifest (expected {path.stem}.yaml)")
            continue
        for msg in svg_errors(path.read_text()):
            errors.append(f"{rel}: {msg}")
    return errors


def catalog_errors(catalog: dict, manifests: list[tuple[str, dict]]) -> list[str]:
    errors: list[str] = []
    entries = {e["key"]: e for e in (catalog.get("skills") or [])}
    seen: set[str] = set()
    for relpath, manifest in manifests:
        key = manifest.get("key")
        seen.add(key)
        entry = entries.get(key)
        if entry is None:
            errors.append(f"{key}: manifest present but missing from catalog.yaml")
            continue
        if entry.get("path") != relpath:
            errors.append(f"{key}: catalog path {entry.get('path')!r} != {relpath!r}")
        if entry.get("version") != manifest.get("version"):
            errors.append(
                f"{key}: catalog version {entry.get('version')!r} != manifest {manifest.get('version')!r}"
            )
    for key in entries:
        if key not in seen:
            errors.append(f"{key}: listed in catalog.yaml but no manifest found")
    return errors


def main() -> int:
    schema = load_schema()
    paths = manifest_paths()
    errors: list[str] = []
    manifests: list[tuple[str, dict]] = []
    for path in paths:
        data = load_yaml(path)
        rel = str(path.relative_to(ROOT))
        manifests.append((rel, data))
        for msg in validate_data(schema, data):
            errors.append(f"{rel}: {msg}")
    if CATALOG_PATH.exists():
        errors += catalog_errors(load_yaml(CATALOG_PATH), manifests)
    else:
        errors.append("catalog.yaml: missing")
    icons = icon_paths()
    errors += icon_errors(icons)
    if errors:
        print("INVALID:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(
        f"OK: {len(paths)} manifest(s) valid and consistent with catalog"
        f" ({len(icons)} icon(s) checked)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
