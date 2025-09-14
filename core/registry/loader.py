"""Registry loader: reads all YAML manifests (Step 5)."""
from __future__ import annotations

import hashlib
import threading
from pathlib import Path
from typing import Dict

import yaml
from yaml import YAMLError

from core.llm import ModelLoadError
from .manifest import ModelManifest

_registry_lock = threading.Lock()
_manifest_cache: Dict[Path, Dict[str, ModelManifest]] = {}


def _iter_manifest_files(registry_dir: Path):
    for path in sorted(registry_dir.glob("*.yaml")):
        if path.is_file():
            yield path


def _load_manifest_file(path: Path) -> ModelManifest:
    """Load a single manifest file with a small robustness tweak.

    If YAML contains tab characters (common accidental edit on Windows), we
    re-try after replacing tabs with two spaces so that a single bad manifest
    does not crash the entire /models endpoint or generation flow.
    """
    raw_text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw_text) or {}
    except YAMLError as e:  # pragma: no cover - defensive branch
        if "\t" in raw_text:
            # Tabs present: attempt tolerant parse
            safe_text = raw_text.replace("\t", "  ")
            try:
                print(
                    f"[WARN] Re-parsing manifest tabs->spaces: {path.name}"
                )
                data = yaml.safe_load(safe_text) or {}
            except Exception as e2:  # noqa: BLE001
                raise ModelLoadError(
                    f"Invalid manifest {path.name}: {e2}"
                ) from e2
        else:
            raise ModelLoadError(f"Invalid manifest {path.name}: {e}") from e
    try:
        return ModelManifest(**data)
    except Exception as e:  # noqa: BLE001
        raise ModelLoadError(f"Invalid manifest {path.name}: {e}") from e


def load_manifests(
    repo_root: str | Path,
    registry_subdir: str = "llm/registry",
) -> Dict[str, ModelManifest]:
    """Load all manifests into an index keyed by id (thread-safe cache)."""
    root = Path(repo_root).resolve()
    with _registry_lock:
        if root in _manifest_cache:
            return _manifest_cache[root]
        registry_dir = root / registry_subdir
        if not registry_dir.exists():
            _manifest_cache[root] = {}
            return _manifest_cache[root]
        index: Dict[str, ModelManifest] = {}
        for mf in _iter_manifest_files(registry_dir):
            manifest = _load_manifest_file(mf)
            if manifest.id in index:
                raise ModelLoadError(
                    f"Duplicate model id in registry: {manifest.id}"
                )
            index[manifest.id] = manifest
        _manifest_cache[root] = index
        return index


def compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_model_checksum(
    manifest: ModelManifest,
    repo_root: str | Path,
    skip: bool = False,
) -> bool:
    if skip:
        return True
    file_path = manifest.resolve_model_path(Path(repo_root))
    if not file_path.exists():
        raise ModelLoadError(f"Model file not found: {file_path}")
    actual = compute_sha256(file_path)
    if actual.lower() != manifest.checksum_sha256.lower():
        raise ModelLoadError(
            "Checksum mismatch for {id}: expected {exp} got {act}".format(
                id=manifest.id, exp=manifest.checksum_sha256, act=actual
            )
        )
    return True


def clear_manifest_cache(repo_root: str | Path | None = None) -> None:
    """Clear cached manifest index.

    If repo_root provided, clear only that entry; else clear all.
    """
    with _registry_lock:
        if repo_root is None:
            _manifest_cache.clear()
        else:
            _manifest_cache.pop(Path(repo_root).resolve(), None)

