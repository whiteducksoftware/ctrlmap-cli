from __future__ import annotations

from typing import Sequence

from ctrlmap_cli.exporters.collection import CollectionExporter


class AssetsExporter(CollectionExporter):
    collection_name = "assets"
    document_title = "Assets"
    list_method = "list_assets"
    response_keys: Sequence[str] = ("assetList", "assetDTOS", "assets", "content", "data")
    file_prefix = "asset"
