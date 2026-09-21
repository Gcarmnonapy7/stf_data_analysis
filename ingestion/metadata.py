"""Metadata and provenance tracking for STF Transparency Platform.

Ensures every ingested raw file is tracked with cryptographic hashes (SHA-256),
timestamps, source URL, version, and record counts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DatasetMetadata:
    dataset_name: str
    source_url: str
    original_filename: str
    file_path: str
    file_hash_sha256: str
    file_size_bytes: int
    row_count: int
    dataset_version: str
    download_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: str = "SUCCESS"
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IngestionMetadataTracker:
    """Manages recording and querying ingestion metadata and provenance manifests."""

    def __init__(self, metadata_dir: Optional[Path | str] = None) -> None:
        if metadata_dir is None:
            # Default to data/metadata relative to project root
            self.metadata_dir = Path(__file__).resolve().parent.parent / "data" / "metadata"
        else:
            self.metadata_dir = Path(metadata_dir)

        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.metadata_dir / "manifest.jsonl"

    @staticmethod
    def calculate_sha256(file_path: Path | str) -> str:
        """Calculates the SHA-256 checksum of a file."""
        path = Path(file_path)
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def record_ingestion(
        self,
        dataset_name: str,
        source_url: str,
        file_path: Path | str,
        row_count: int,
        dataset_version: str = "v1.0",
        extra: Optional[Dict[str, Any]] = None,
    ) -> DatasetMetadata:
        """Computes checksum and logs metadata entry into manifest.jsonl."""
        path = Path(file_path)
        file_hash = self.calculate_sha256(path)
        file_size = path.stat().st_size

        meta = DatasetMetadata(
            dataset_name=dataset_name,
            source_url=source_url,
            original_filename=path.name,
            file_path=str(path.resolve()),
            file_hash_sha256=file_hash,
            file_size_bytes=file_size,
            row_count=row_count,
            dataset_version=dataset_version,
            extra=extra or {},
        )

        with open(self.manifest_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(meta.to_dict(), ensure_ascii=False) + "\n")

        return meta

    def get_latest_manifest(self, dataset_name: Optional[str] = None) -> Optional[DatasetMetadata]:
        """Retrieves the latest metadata record for a given dataset or overall."""
        records = self.list_manifests(dataset_name)
        return records[-1] if records else None

    def list_manifests(self, dataset_name: Optional[str] = None) -> List[DatasetMetadata]:
        """Reads all recorded manifests from disk."""
        if not self.manifest_file.exists():
            return []

        results: List[DatasetMetadata] = []
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if dataset_name is None or data.get("dataset_name") == dataset_name:
                        results.append(DatasetMetadata(**data))
                except Exception:
                    continue
        return results
