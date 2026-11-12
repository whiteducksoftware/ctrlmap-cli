from __future__ import annotations

from typing import Sequence

from ctrlmap_cli.exporters.collection import CollectionExporter


class AssetTypesExporter(CollectionExporter):
    collection_name = "asset types"
    document_title = "Asset Types"
    list_method = "list_asset_types"
    response_keys: Sequence[str] = (
        "assetTypeList", "assetTypeDTOS", "assetTypes", "content", "data",
    )
    file_prefix = "asset-type"
