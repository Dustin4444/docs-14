"""Tests for the package_versions preprocessor."""

from pathlib import Path

from pipeline.preprocessors.package_versions import (
    load_versions,
    substitute_versions,
)


def test_substitute_known_placeholder() -> None:
    """Known placeholders are replaced with the mapped version."""
    versions = {"LANGCHAIN_PY_VERSION": "1.2.3"}
    content = "pip install langchain=={{LANGCHAIN_PY_VERSION}}"
    assert substitute_versions(content, versions) == "pip install langchain==1.2.3"


def test_substitute_multiple_placeholders() -> None:
    """All occurrences across multiple placeholders are substituted."""
    versions = {
        "LANGCHAIN_JS_VERSION": "1.0.5",
        "LANGCHAIN_CORE_JS_VERSION": "1.0.2",
    }
    content = (
        "npm install langchain@{{LANGCHAIN_JS_VERSION}} "
        "@langchain/core@{{LANGCHAIN_CORE_JS_VERSION}}"
    )
    assert (
        substitute_versions(content, versions)
        == "npm install langchain@1.0.5 @langchain/core@1.0.2"
    )


def test_unknown_placeholder_left_untouched() -> None:
    """Unknown placeholders are preserved so unrelated tokens are safe."""
    versions = {"LANGCHAIN_PY_VERSION": "1.2.3"}
    content = "hello {{UNKNOWN_TOKEN}} world"
    assert substitute_versions(content, versions) == "hello {{UNKNOWN_TOKEN}} world"


def test_empty_versions_map_is_noop() -> None:
    """An empty versions map leaves content untouched."""
    content = "pip install langchain=={{LANGCHAIN_PY_VERSION}}"
    assert substitute_versions(content, {}) == content


def test_placeholder_with_internal_whitespace() -> None:
    """Whitespace inside the placeholder braces is tolerated."""
    versions = {"LANGGRAPH_PY_VERSION": "1.0.0"}
    content = "pip install langgraph=={{ LANGGRAPH_PY_VERSION }}"
    assert substitute_versions(content, versions) == "pip install langgraph==1.0.0"


def test_load_versions_from_file(tmp_path: Path) -> None:
    """load_versions parses a versions.yml file into a placeholder map."""
    versions_file = tmp_path / "versions.yml"
    versions_file.write_text(
        "packages:\n"
        "- name: langchain\n"
        "  registry: pypi\n"
        "  placeholder: LANGCHAIN_PY_VERSION\n"
        "  version: 1.2.3\n"
        "- name: langgraph\n"
        "  registry: pypi\n"
        "  placeholder: LANGGRAPH_PY_VERSION\n"
        "  version: 1.0.0\n",
        encoding="utf-8",
    )
    load_versions.cache_clear()
    try:
        mapping = load_versions(versions_file)
    finally:
        load_versions.cache_clear()

    assert mapping == {
        "LANGCHAIN_PY_VERSION": "1.2.3",
        "LANGGRAPH_PY_VERSION": "1.0.0",
    }


def test_load_versions_missing_file(tmp_path: Path) -> None:
    """A missing versions.yml yields an empty mapping rather than raising."""
    load_versions.cache_clear()
    try:
        assert load_versions(tmp_path / "does-not-exist.yml") == {}
    finally:
        load_versions.cache_clear()


def test_repo_versions_yml_loads() -> None:
    """The checked-in versions.yml parses and defines expected placeholders."""
    load_versions.cache_clear()
    try:
        mapping = load_versions()
    finally:
        load_versions.cache_clear()

    assert "LANGCHAIN_PY_VERSION" in mapping
    assert "LANGGRAPH_PY_VERSION" in mapping
    assert "DEEPAGENTS_PY_VERSION" in mapping
    assert "LANGCHAIN_JS_VERSION" in mapping
    assert "LANGGRAPH_JS_VERSION" in mapping
