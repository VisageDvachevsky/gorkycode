from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

__all__ = [
    "PoiDataError",
    "ensure_project_root",
    "ensure_pythonpath",
    "resolve_poi_json_path",
    "load_poi_data",
]


class PoiDataError(RuntimeError):

    def __init__(self, message: str, *, path: Path | None = None, checked: Sequence[Path] | None = None):
        super().__init__(message)
        self.path = path
        self.checked: List[Path] = list(checked or [])


def ensure_pythonpath(*paths: os.PathLike[str] | str) -> None:
    """Ensure the provided directories are present on ``sys.path``.

    Paths that do not exist are ignored silently to keep the helper resilient in
    container environments where optional directories might be absent.
    """

    for path in paths:
        if not path:
            continue
        candidate = Path(path).expanduser()
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_dir():
            str_path = str(resolved)
            if str_path not in sys.path:
                sys.path.insert(0, str_path)


def ensure_project_root(*hints: os.PathLike[str] | str) -> Path:
    """Detect and export the project root path.

    ``PROJECT_ROOT`` is determined using (in priority order):

    1. The current value of the ``PROJECT_ROOT`` environment variable.
    2. Explicit hints provided to the function.
    3. Ancestors of this utility module and the current working directory.
    4. ``/app`` as a common default inside our containers.

    The first directory containing either ``data/`` or ``app/`` wins.  When no
    suitable directory is found we fall back to the parent of the ``scripts/``
    directory that houses this module.
    """

    scripts_dir = Path(__file__).resolve().parent

    candidates: list[Path] = []

    env_value = os.getenv("PROJECT_ROOT")
    if env_value:
        candidates.append(Path(env_value).expanduser())

    for hint in hints:
        if hint:
            candidates.append(Path(hint))

    candidates.extend(parent for parent in scripts_dir.parents)
    candidates.append(Path.cwd())
    candidates.append(Path("/app"))

    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue

        if not resolved.exists():
            continue

        if (resolved / "data").is_dir() or (resolved / "app").is_dir():
            os.environ.setdefault("PROJECT_ROOT", str(resolved))
            return resolved

    fallback = scripts_dir.parent.resolve()
    os.environ.setdefault("PROJECT_ROOT", str(fallback))
    return fallback


def _iter_candidate_paths(additional: Iterable[os.PathLike[str] | str] | None = None) -> Iterable[Path]:
    scripts_dir = Path(__file__).resolve().parent
    repo_root = Path(os.getenv("PROJECT_ROOT") or scripts_dir.parent)
    cwd = Path.cwd()

    env_candidates: list[Path] = []
    for env_name in ("POI_JSON_PATH", "POI_DATA_PATH"):
        env_value = os.getenv(env_name)
        if env_value:
            env_candidates.append(Path(env_value).expanduser())

    project_root_env = os.getenv("PROJECT_ROOT")
    if project_root_env:
        env_candidates.append(Path(project_root_env).expanduser() / "data" / "poi.json")

    default_candidates = [
        scripts_dir / "poi.json",
        repo_root / "data" / "poi.json",
        cwd / "data" / "poi.json",
        Path("/data/poi.json"),
        Path("/app/data/poi.json"),
    ]

    combined: List[Path] = []
    for sequence in (env_candidates, list(additional or []), default_candidates):
        for candidate in sequence:
            path = Path(candidate)
            if path not in combined:
                combined.append(path)
    return combined


def resolve_poi_json_path(*, preferred_paths: Iterable[os.PathLike[str] | str] | None = None, require_exists: bool = True) -> Path:
    """Return the first existing POI JSON path.

    Args:
        preferred_paths: Optional iterable of extra paths to check before defaults.
        require_exists: If True, raise :class:`PoiDataError` when nothing is found.
    """

    checked: List[Path] = []
    empty_candidate: Path | None = None

    for candidate in _iter_candidate_paths(preferred_paths):
        candidate = candidate.expanduser()
        checked.append(candidate)
        if candidate.is_file():
            if candidate.stat().st_size == 0:
                empty_candidate = candidate
                continue
            return candidate

    if require_exists:
        if empty_candidate is not None:
            raise PoiDataError(f"POI dataset file is empty: {empty_candidate}", path=empty_candidate, checked=checked)
        raise PoiDataError(
            "POI dataset file not found. Checked: " + ", ".join(str(path) for path in checked),
            path=None,
            checked=checked,
        )

    return checked[-1] if checked else Path("data/poi.json")


def load_poi_data(path: os.PathLike[str] | str | None = None) -> list[dict]:
    """Load POI data from JSON ensuring valid structure."""

    resolved_path = Path(path) if path else resolve_poi_json_path()

    if not resolved_path.is_file():
        raise PoiDataError(
            f"POI dataset file does not exist: {resolved_path}",
            path=resolved_path,
        )

    if resolved_path.stat().st_size == 0:
        raise PoiDataError(f"POI dataset file is empty: {resolved_path}", path=resolved_path)

    try:
        with resolved_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise PoiDataError(f"Invalid JSON in {resolved_path}: {exc}", path=resolved_path) from exc

    if not isinstance(data, list):
        raise PoiDataError(
            f"Expected POI dataset to be a list, got {type(data).__name__} in {resolved_path}",
            path=resolved_path,
        )

    return data
