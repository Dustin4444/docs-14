"""Substitute package version placeholders in markdown content.

Reads `versions.yml` at the repo root to get the latest published PyPI/npm
versions and replaces tokens like `{{LANGCHAIN_PY_VERSION}}` with the
corresponding version string.

Install/upgrade snippets in the docs reference these tokens, so the docs
always show the latest published version without manual updates.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_YML = REPO_ROOT / "versions.yml"

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Z0-9_]+)\s*\}\}")


@lru_cache(maxsize=1)
def load_versions(path: Path = VERSIONS_YML) -> dict[str, str]:
    """Load placeholder->version mapping from versions.yml.

    Returns an empty dict if the file is missing or malformed.
    """
    if not path.exists():
        logger.warning("versions.yml not found at %s", path)
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError:
        logger.exception("Failed to parse %s", path)
        return {}

    mapping: dict[str, str] = {}
    for pkg in data.get("packages", []) or []:
        placeholder = pkg.get("placeholder")
        version = pkg.get("version")
        if placeholder and version:
            mapping[str(placeholder)] = str(version)
    return mapping


def substitute_versions(content: str, versions: dict[str, str] | None = None) -> str:
    """Replace version placeholders in content with values from versions.yml.

    Unknown placeholders are left untouched so unrelated `{{ ... }}` tokens
    (e.g., MDX expressions) are not accidentally rewritten.
    """
    version_map = load_versions() if versions is None else versions
    if not version_map:
        return content

    def _replace(match: re.Match) -> str:
        token = match.group(1)
        if token in version_map:
            return version_map[token]
        return match.group(0)

    return _PLACEHOLDER_RE.sub(_replace, content)
