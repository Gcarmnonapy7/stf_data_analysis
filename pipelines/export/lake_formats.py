"""Lakehouse Table Exporter for Delta Lake and Apache Iceberg formats.

Enables the STF Transparency Platform to interoperate with modern Lakehouse ecosystems:
- Delta Lake (Linux Foundation / Databricks): ACID transaction log (_delta_log) + Parquet parts.
- Apache Iceberg: Table metadata specification v2 + partitioned Parquet data.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import polars as pl
import pyarrow.parquet as pq


class LakehouseExporter:
    """Exports DuckDB / Curated Parquet models into open Lakehouse table formats."""

    def __init__(self, data_dir: Optional[Path | str] = None) -> None:
        project_root = Path(__file__).resolve().parent.parent.parent
        self.data_dir = Path(data_dir) if data_dir else project_root / "data"
        self.curated_dir = self.data_dir / "curated"
        self.exports_dir = self.data_dir / "exports"
        self.delta_dir = self.exports_dir / "delta"
        self.iceberg_dir = self.exports_dir / "iceberg"
        self.db_path = self.curated_dir / "stf_warehouse.duckdb"

    def list_available_tables(self) -> List[str]:
        """Returns list of curated tables available for export."""
        parquet_files = list(self.curated_dir.glob("*.parquet"))
        return [p.stem for p in parquet_files]

    def export_to_delta(self, table_name: str) -> Path:
        """Exports a table into a valid Delta Lake table structure with _delta_log."""
        source_parquet = self.curated_dir / f"{table_name}.parquet"
        if not source_parquet.exists():
            raise FileNotFoundError(f"Curated table {table_name} not found at {source_parquet}")

        target_table_dir = self.delta_dir / table_name
        target_table_dir.mkdir(parents=True, exist_ok=True)
        delta_log_dir = target_table_dir / "_delta_log"
        delta_log_dir.mkdir(parents=True, exist_ok=True)

        # Read source data via Polars
        df = pl.read_parquet(source_parquet)
        table_id = str(uuid.uuid4())
        part_name = f"part-00000-{uuid.uuid4()}.zstd.parquet"
        part_file = target_table_dir / part_name

        # Write Parquet part
        df.write_parquet(part_file, compression="zstd")
        part_size = part_file.stat().st_size
        modification_time = int(time.time() * 1000)

        # Build schema string in Spark/Delta format
        fields = []
        for col_name, dtype in zip(df.columns, df.dtypes):
            type_str = "string"
            if dtype in (pl.Int64, pl.Int32):
                type_str = "long" if dtype == pl.Int64 else "integer"
            elif dtype in (pl.Float64, pl.Float32):
                type_str = "double"
            elif dtype == pl.Boolean:
                type_str = "boolean"
            elif dtype == pl.Date:
                type_str = "date"
            fields.append({
                "name": col_name,
                "type": type_str,
                "nullable": True,
                "metadata": {},
            })

        schema_struct = {
            "type": "struct",
            "fields": fields,
        }

        # Construct Delta commit actions
        commit_actions = [
            {
                "commitInfo": {
                    "timestamp": modification_time,
                    "operation": "WRITE",
                    "operationParameters": {"mode": "Overwrite", "partitionBy": "[]"},
                    "engineInfo": "STF-Transparency-Platform/1.0",
                }
            },
            {
                "protocol": {
                    "minReaderVersion": 1,
                    "minWriterVersion": 2,
                }
            },
            {
                "metaData": {
                    "id": table_id,
                    "format": {"provider": "parquet", "options": {}},
                    "schemaString": json.dumps(schema_struct),
                    "partitionColumns": [],
                    "configuration": {},
                    "createdTime": modification_time,
                }
            },
            {
                "add": {
                    "path": part_name,
                    "size": part_size,
                    "modificationTime": modification_time,
                    "dataChange": True,
                    "stats": json.dumps({
                        "numRecords": df.height,
                    }),
                }
            },
        ]

        commit_file = delta_log_dir / "00000000000000000000.json"
        with open(commit_file, "w", encoding="utf-8") as f:
            for action in commit_actions:
                f.write(json.dumps(action, ensure_ascii=False) + "\n")

        return target_table_dir

    def export_to_iceberg(self, table_name: str) -> Path:
        """Exports a table into Apache Iceberg metadata v2 specification directory."""
        source_parquet = self.curated_dir / f"{table_name}.parquet"
        if not source_parquet.exists():
            raise FileNotFoundError(f"Curated table {table_name} not found at {source_parquet}")

        target_table_dir = self.iceberg_dir / table_name
        data_dir = target_table_dir / "data"
        metadata_dir = target_table_dir / "metadata"
        data_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        df = pl.read_parquet(source_parquet)
        data_file_name = f"data-00000-{uuid.uuid4()}.zstd.parquet"
        data_file_path = data_dir / data_file_name
        df.write_parquet(data_file_path, compression="zstd")

        timestamp_ms = int(time.time() * 1000)
        table_uuid = str(uuid.uuid4())

        # Iceberg schema definitions
        fields = []
        for idx, (col_name, dtype) in enumerate(zip(df.columns, df.dtypes), 1):
            type_str = "string"
            if dtype in (pl.Int64, pl.Int32):
                type_str = "long" if dtype == pl.Int64 else "int"
            elif dtype in (pl.Float64, pl.Float32):
                type_str = "double"
            elif dtype == pl.Boolean:
                type_str = "boolean"
            elif dtype == pl.Date:
                type_str = "date"
            fields.append({
                "id": idx,
                "name": col_name,
                "required": False,
                "type": type_str,
            })

        metadata_v2 = {
            "format-version": 2,
            "table-uuid": table_uuid,
            "location": str(target_table_dir.resolve()),
            "last-sequence-number": 1,
            "last-updated-ms": timestamp_ms,
            "last-column-id": len(fields),
            "current-schema-id": 0,
            "schemas": [
                {
                    "type": "struct",
                    "schema-id": 0,
                    "fields": fields,
                }
            ],
            "default-spec-id": 0,
            "partition-specs": [
                {
                    "spec-id": 0,
                    "fields": [],
                }
            ],
            "last-partition-id": 999,
            "current-snapshot-id": 1000000000001,
            "snapshots": [
                {
                    "snapshot-id": 1000000000001,
                    "sequence-number": 1,
                    "timestamp-ms": timestamp_ms,
                    "summary": {
                        "operation": "append",
                        "total-records": str(df.height),
                        "total-data-files": "1",
                        "total-files-size": str(data_file_path.stat().st_size),
                    },
                    "manifest-list": f"metadata/snap-1000000000001-{uuid.uuid4()}.avro",
                }
            ],
        }

        meta_file = metadata_dir / "v1.metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata_v2, f, indent=2, ensure_ascii=False)

        # Version hint for Iceberg catalogs
        (metadata_dir / "version-hint.text").write_text("1\n", encoding="utf-8")

        return target_table_dir

    def export_all(self, target_format: str = "both") -> Dict[str, Any]:
        """Exports all curated tables to specified open format(s)."""
        tables = self.list_available_tables()
        results: Dict[str, Any] = {"exported_tables": tables, "formats": {}}

        if target_format in ("delta", "both"):
            results["formats"]["delta"] = {}
            for t in tables:
                p = self.export_to_delta(t)
                results["formats"]["delta"][t] = str(p.resolve())

        if target_format in ("iceberg", "both"):
            results["formats"]["iceberg"] = {}
            for t in tables:
                p = self.export_to_iceberg(t)
                results["formats"]["iceberg"][t] = str(p.resolve())

        return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Export STF Lakehouse tables to Delta Lake and Apache Iceberg")
    parser.add_argument("--format", default="both", choices=["delta", "iceberg", "both"], help="Target format")
    parser.add_argument("--table", default="all", help="Table name or 'all'")
    args = parser.parse_args()

    exporter = LakehouseExporter()
    if args.table == "all":
        res = exporter.export_all(target_format=args.format)
        print(f"Export completed: {json.dumps(res, indent=2)}")
    else:
        if args.format in ("delta", "both"):
            p = exporter.export_to_delta(args.table)
            print(f"Exported {args.table} to Delta Lake at: {p}")
        if args.format in ("iceberg", "both"):
            p = exporter.export_to_iceberg(args.table)
            print(f"Exported {args.table} to Apache Iceberg at: {p}")


if __name__ == "__main__":
    main()

