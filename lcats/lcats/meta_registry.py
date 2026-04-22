"""Workspace project registry helpers for the meta register CLI slice."""

import datetime
import pathlib
import re
from typing import Any
from urllib import parse


PROJECTS_DIR_NAME = "projects"
PROJECT_DIR_DEFAULT = "project"


def _toml_string(value: str) -> str:
    """Return a TOML basic string literal for the supplied value."""
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\b", "\\b")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\f", "\\f")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def _normalise_slug(value: str) -> str:
    """Return a lowercase slug suitable for registry directory naming."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def infer_names(repo_locator: str) -> tuple[str, str]:
    """Infer display and short names from an arbitrary repository locator."""
    parsed = parse.urlparse(repo_locator)
    candidate = parsed.path or repo_locator
    candidate = candidate.rstrip("/")
    base = pathlib.Path(candidate).name or "project"
    base = re.sub(r"\.git$", "", base)
    short_name = _normalise_slug(base)
    display_name = " ".join(part.capitalize() for part in short_name.split("-"))
    return display_name, short_name


def detect_setup_state(
    repo_locator: str, project_dir: str = PROJECT_DIR_DEFAULT
) -> str:
    """Detect whether a local repo appears to contain an LRH project directory."""
    maybe_local = pathlib.Path(repo_locator)
    if maybe_local.exists() and maybe_local.is_dir():
        if (maybe_local / project_dir).exists():
            return "lrh_project_present"
    return "not_set_up"


def _extract_value(line: str) -> str | None:
    match = re.match(r'^\s*([a-z_]+)\s*=\s*"([^"]*)"\s*$', line.strip())
    if not match:
        return None
    return match.group(2)


def _read_record(path: pathlib.Path) -> dict[str, str]:
    record: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("id ="):
            value = _extract_value(line)
            if value is not None:
                record["id"] = value
        if line.strip().startswith("repo_locator ="):
            value = _extract_value(line)
            if value is not None:
                record["repo_locator"] = value
    return record


def _existing_records(projects_dir: pathlib.Path) -> list[dict[str, Any]]:
    records = []
    if not projects_dir.exists():
        return records
    for path in sorted(projects_dir.glob("*.toml")):
        data = _read_record(path)
        data["path"] = path
        records.append(data)
    return records


def _next_project_id(records: list[dict[str, Any]]) -> str:
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    last_number = 0
    for record in records:
        project_id = record.get("id", "")
        match = re.match(r"^proj-(\d{8})-(\d{3})$", project_id)
        if match and match.group(1) == today:
            last_number = max(last_number, int(match.group(2)))
    next_number = last_number + 1
    return f"proj-{today}-{next_number:03d}"


def _ensure_unique_filename(projects_dir: pathlib.Path, directory_name: str) -> str:
    candidate = directory_name
    counter = 1
    while (projects_dir / f"{candidate}.toml").exists():
        counter += 1
        candidate = f"{directory_name}-{counter}"
    return candidate


def register_project(
    workspace_root: pathlib.Path,
    repo_locator: str,
    force: bool = False,
    project_dir: str = PROJECT_DIR_DEFAULT,
) -> dict[str, str]:
    """Create and persist a workspace registry entry for a project."""
    projects_dir = workspace_root / PROJECTS_DIR_NAME
    projects_dir.mkdir(parents=True, exist_ok=True)
    records = _existing_records(projects_dir)

    for record in records:
        if record.get("repo_locator") == repo_locator and not force:
            raise ValueError(f"Project already registered for locator: {repo_locator}")

    display_name, short_name = infer_names(repo_locator)
    setup_state = detect_setup_state(repo_locator, project_dir=project_dir)
    project_id = _next_project_id(records)
    directory_name = _ensure_unique_filename(projects_dir, short_name)

    record = {
        "id": project_id,
        "display_name": display_name,
        "short_name": short_name,
        "status": "active",
        "setup_state": setup_state,
        "repo_locator": repo_locator,
        "project_dir": project_dir,
        "directory_name": directory_name,
    }

    text = (
        "[project]\n"
        f"id = {_toml_string(record['id'])}\n"
        f"display_name = {_toml_string(record['display_name'])}\n"
        f"short_name = {_toml_string(record['short_name'])}\n"
        f"status = {_toml_string(record['status'])}\n"
        f"setup_state = {_toml_string(record['setup_state'])}\n\n"
        "[identity]\n"
        f"repo_locator = {_toml_string(record['repo_locator'])}\n"
        f"project_dir = {_toml_string(record['project_dir'])}\n\n"
        "[registry]\n"
        f"directory_name = {_toml_string(record['directory_name'])}\n"
    )

    (projects_dir / f"{directory_name}.toml").write_text(text, encoding="utf-8")
    return record
