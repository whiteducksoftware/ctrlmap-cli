from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from ctrlmap_cli.exceptions import ApiError
from ctrlmap_cli.exporters.asset_types import AssetTypesExporter
from ctrlmap_cli.exporters.assets import AssetsExporter


@pytest.mark.parametrize(
    "exporter_type,method,response",
    [
        (AssetsExporter, "list_assets", {"assetList": [
            {"id": 17, "assetName": "Laptop", "owner": "Example"},
        ]}),
        (AssetTypesExporter, "list_asset_types", [
            {"id": 4, "name": "Workstation"},
        ]),
    ],
)
def test_collection_export_writes_markdown_and_index(
    exporter_type: type,
    method: str,
    response: object,
    tmp_path: Path,
) -> None:
    client = MagicMock()
    getattr(client, method).return_value = response
    exporter = exporter_type(client, tmp_path)

    exporter.export()

    files = list(tmp_path.glob("*.md"))
    assert len(files) == 2
    exported_file = next(path for path in files if path.name != "index.md")
    frontmatter = exported_file.read_text(encoding="utf-8").split("---\n")[1]
    assert yaml.safe_load(frontmatter)["id"] in (17, 4)
    assert exported_file.stem in (("17", "Laptop") if method == "list_assets" else ("4", "Workstation"))
    assert exported_file.name in (tmp_path / "index.md").read_text(encoding="utf-8")
    getattr(client, method).assert_called_once_with()


def test_assets_export_preserves_raw_json_when_requested(tmp_path: Path) -> None:
    client = MagicMock()
    client.list_assets.return_value = {"assets": [{"id": 1, "name": "Router"}]}
    exporter = AssetsExporter(client, tmp_path, keep_raw_json=True)

    exporter.export()

    assert json.loads((tmp_path / "1.json").read_text(encoding="utf-8")) == {
        "id": 1,
        "name": "Router",
    }


def test_collection_export_handles_empty_results(tmp_path: Path) -> None:
    client = MagicMock()
    client.list_assets.return_value = []

    AssetsExporter(client, tmp_path).export()

    index = (tmp_path / "index.md").read_text(encoding="utf-8")
    assert "0 assets exported" in index


@pytest.mark.parametrize("response", [{"unexpected": []}, "invalid"])
def test_collection_export_rejects_unexpected_response(
    response: object,
    tmp_path: Path,
) -> None:
    client = MagicMock()
    client.list_assets.return_value = response

    with pytest.raises(ApiError, match="Unexpected response"):
        AssetsExporter(client, tmp_path).export()


def test_collection_export_rejects_non_object_records(tmp_path: Path) -> None:
    client = MagicMock()
    client.list_assets.return_value = [None]

    with pytest.raises(ApiError, match="Unexpected response"):
        AssetsExporter(client, tmp_path).export()


def test_collection_export_disambiguates_duplicate_ids(tmp_path: Path) -> None:
    client = MagicMock()
    client.list_assets.return_value = [
        {"id": 1, "name": "First"},
        {"id": 1, "name": "Second"},
    ]

    AssetsExporter(client, tmp_path).export()

    assert (tmp_path / "1.md").is_file()
    assert (tmp_path / "1-2.md").is_file()
    assert "Second" in (tmp_path / "1-2.md").read_text(encoding="utf-8")


def test_collection_single_export_reports_unsupported(tmp_path: Path) -> None:
    with pytest.raises(ApiError, match="bulk export"):
        AssetsExporter(MagicMock(), tmp_path).export_single("1")
