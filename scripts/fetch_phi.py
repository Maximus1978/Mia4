#!/usr/bin/env python
"""Fetch phi-3.5-mini-instruct GGUF and update manifest checksum.

Usage:
    python scripts/fetch_phi.py \
        --model phi-3.5-mini-instruct-q4_0 \
        --repo microsoft/Phi-3.5-mini-instruct \
        --filename Phi-3.5-mini-instruct-q4_0.gguf

Defaults assume quantized GGUF file exists in HF repo (adjust filename).
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download, list_repo_files
import yaml

REG_DIR = Path('llm/registry')
MODELS_DIR = Path('models')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def update_manifest(model_id: str, file_rel_path: str, checksum: str):
    manifest_path = REG_DIR / f'{model_id}.yaml'
    if not manifest_path.exists():
        raise SystemExit(f'Manifest not found: {manifest_path}')
    data = yaml.safe_load(manifest_path.read_text(encoding='utf-8')) or {}
    data['path'] = file_rel_path
    data['checksum_sha256'] = checksum
    manifest_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding='utf-8',
    )
    print(f'[manifest-updated] {manifest_path} checksum={checksum}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='phi-3.5-mini-instruct-q4_0')
    ap.add_argument('--repo', default='microsoft/Phi-3.5-mini-instruct')
    ap.add_argument(
        '--filename',
        default='Phi-3.5-mini-instruct-q4_0.gguf',
        help='Exact GGUF filename (if known)',
    )
    ap.add_argument(
        '--auto',
        action='store_true',
        help='Try common quant filenames if specified one not found',
    )
    ap.add_argument('--revision', default=None)
    args = ap.parse_args()

    MODELS_DIR.mkdir(exist_ok=True)

    print(
        f'[download] repo={args.repo} file={args.filename} '
        f'revision={args.revision or "main"}'
    )
    try:
        local_path = hf_hub_download(
            repo_id=args.repo,
            filename=args.filename,
            revision=args.revision,
            local_dir=str(MODELS_DIR),
        )
    except Exception as e:  # noqa: BLE001
        if not args.auto:
            raise
        print(
            f'[warn] primary filename not found ({e}); '
            'listing repo files for fallback...'
        )
        files = list_repo_files(args.repo, revision=args.revision)
        ggufs = [f for f in files if f.lower().endswith('.gguf')]
        # simple preference order
        preference = [
            'q4_k_m', 'q4km', 'q4_0', 'q3_k_m', 'q5_k_m', 'q6_k', 'q8_0'
        ]
        candidate = None
        for p in preference:
            for f in ggufs:
                if p in f.lower():
                    candidate = f
                    break
            if candidate:
                break
        if not candidate and ggufs:
            candidate = ggufs[0]
        if not candidate:
            raise SystemExit('[error] No GGUF files found in repo')
        print(f'[fallback] trying candidate {candidate}')
        local_path = hf_hub_download(
            repo_id=args.repo,
            filename=candidate,
            revision=args.revision,
            local_dir=str(MODELS_DIR),
        )
    local_path = Path(local_path)
    if not local_path.exists():
        raise SystemExit('Downloaded file missing')
    checksum = sha256_file(local_path)
    rel_path = local_path.relative_to(Path('.')).as_posix()
    update_manifest(args.model, rel_path, checksum)
    print('[done]')


if __name__ == '__main__':
    main()
