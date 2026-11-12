from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Set, Tuple

from ctrlmap_cli.exceptions import ApiError
from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.formatters.markdown_formatter import MarkdownFormatter


class CollectionExporter(BaseExporter):
    collection_name = ""
    document_title = ""
    list_method = ""
    response_keys: Sequence[str] = ()
    file_prefix = ""

    def export(self) -> None:
        self._ensure_output_dir()
        self._log(f"Exporting {self.collection_name}...")

        response = getattr(self.client, self.list_method)()
        records = self._extract_records(response)
        used_stems: Set[str] = set()
        exported: List[Tuple[str, str]] = []

        for index, record in enumerate(records, start=1):
            title = self._record_title(record, index)
            stem = self._file_stem(record, title, index, used_stems)
            md_content = MarkdownFormatter.render(
                title=title[:110],
                body="",
                frontmatter=record,
            )
            md_path = self.output_dir / f"{stem}.md"
            if self._should_write(md_path):
                md_path.write_text(md_content, encoding="utf-8")

            if self.keep_raw_json:
                json_path = self.output_dir / f"{stem}.json"
                if self._should_write(json_path):
                    self._json_formatter.write(record, json_path)
            exported.append((stem, title))

        self._write_index(exported)
        self._log(
            f"Exporting {self.collection_name}... done ({len(records)} records)"
        )

    def export_single(self, item_code: str) -> None:
        raise ApiError(
            f"Single-item export is not supported for {self.collection_name}. "
            "Use the bulk export option instead."
        )

    def _extract_records(self, response: Any) -> List[Dict[str, Any]]:
        if isinstance(response, list):
            records: Any = response
        elif isinstance(response, dict):
            records = None
            for key in self.response_keys:
                value = response.get(key)
                if isinstance(value, list):
                    records = value
                    break
        else:
            records = None

        if records is None or any(not isinstance(item, dict) for item in records):
            raise ApiError(
                f"Unexpected response while exporting {self.collection_name}. "
                "The ControlMap API response format may have changed."
            )
        return records

    def _record_title(self, record: Dict[str, Any], index: int) -> str:
        for key in (
            "name", "assetName", "type", "assetTypeName", "title",
            "code", "assetCode", "id",
        ):
            value = record.get(key)
            if value is not None and str(value).strip():
                return str(value).strip().replace("\r", " ").replace("\n", " ")
        return f"{self.document_title} {index}"

    def _file_stem(
        self,
        record: Dict[str, Any],
        title: str,
        index: int,
        used_stems: Set[str],
    ) -> str:
        identifier = record.get("code") or record.get("assetCode") or record.get("id")
        if identifier is None or not str(identifier).strip():
            identifier = title
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(identifier)).strip(".-_")
        if not slug:
            slug = f"{self.file_prefix}-{index}"
        base_stem = slug[:80]
        stem = base_stem
        count = 2
        while stem in used_stems:
            stem = f"{base_stem[:72]}-{count}"
            count += 1
        used_stems.add(stem)
        return stem

    def _write_index(self, exported: List[Tuple[str, str]]) -> None:
        generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        body = [f"{len(exported)} {self.collection_name} exported on {generated_date}.", ""]
        for stem, _title in exported:
            body.extend((f"## [{stem}]({stem}.md)", ""))

        content = MarkdownFormatter.render(
            title=self.document_title,
            body="\n".join(body),
            frontmatter={"generated": generated, "document_count": len(exported)},
        )
        index_path = self.output_dir / "index.md"
        if self._should_write(index_path):
            index_path.write_text(content, encoding="utf-8")
