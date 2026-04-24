"""Update latest published versions in versions.yml from PyPI and npm.

Fetches the latest stable (non pre-release) version for each package in
versions.yml and writes it back. Run on a schedule via
.github/workflows/update-package-versions.yml.

Run manually with: uv run scripts/update_package_versions.py
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import requests
from ruamel.yaml import YAML

yaml = YAML()
yaml.preserve_quotes = True
yaml.width = 4096

VERSIONS_YML = Path(__file__).parents[1] / "versions.yml"
TIMEOUT_SECONDS = 15

_PRERELEASE_RE = re.compile(r"[a-zA-Z]")


def _is_stable(version: str) -> bool:
    """Return True if the version string looks like a stable release."""
    return not _PRERELEASE_RE.search(version)


def _get_pypi_latest(package: str) -> str:
    """Fetch the latest stable version of a PyPI package."""
    url = f"https://pypi.org/pypi/{package}/json"
    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()

    info_version = data.get("info", {}).get("version")
    if info_version and _is_stable(info_version):
        return info_version

    releases = data.get("releases", {}) or {}
    stable = [v for v in releases if _is_stable(v) and releases[v]]
    if not stable:
        msg = f"No stable release found for PyPI package {package!r}"
        raise RuntimeError(msg)

    def _version_key(v: str) -> tuple[int, ...]:
        parts: list[int] = []
        for part in v.split("."):
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(0)
        return tuple(parts)

    stable.sort(key=_version_key)
    return stable[-1]


def _get_npm_latest(package: str) -> str:
    """Fetch the latest stable version of an npm package (dist-tags.latest)."""
    # The registry URL-encodes "@" and "/" automatically for scoped packages.
    url = f"https://registry.npmjs.org/{package}"
    response = requests.get(
        url,
        timeout=TIMEOUT_SECONDS,
        headers={"Accept": "application/vnd.npm.install-v1+json"},
    )
    response.raise_for_status()
    data = response.json()

    latest = (data.get("dist-tags") or {}).get("latest")
    if not latest:
        msg = f"No 'latest' dist-tag found for npm package {package!r}"
        raise RuntimeError(msg)
    return latest


def _get_latest(package: str, registry: str) -> str:
    """Fetch the latest stable version from the given registry."""
    if registry == "pypi":
        return _get_pypi_latest(package)
    if registry == "npm":
        return _get_npm_latest(package)
    msg = f"Unknown registry {registry!r} for package {package!r}"
    raise ValueError(msg)


def main() -> int:
    """Update versions.yml in place with the latest published versions."""
    with VERSIONS_YML.open() as f:
        data = yaml.load(f)

    now = datetime.now(UTC).isoformat()
    changed = False

    for pkg in data["packages"]:
        name = pkg["name"]
        registry = pkg["registry"]
        try:
            latest = _get_latest(name, registry)
        except Exception as e:  # noqa: BLE001
            print(f"skip {registry}:{name}: {e}")
            continue

        if pkg.get("version") != latest:
            print(f"update {registry}:{name}: {pkg.get('version')} -> {latest}")
            pkg["version"] = latest
            changed = True
        else:
            print(f"ok     {registry}:{name}: {latest}")
        pkg["updated_at"] = now

    with VERSIONS_YML.open("w") as f:
        yaml.dump(data, f)

    print("changes committed" if changed else "no version changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
