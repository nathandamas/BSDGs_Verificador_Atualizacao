from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import ScanSummary
from .paths import reports_dir


class ReportWriter:
    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or reports_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        summary: ScanSummary,
        file_rows: list[dict[str, Any]],
        layer_rows: list[dict[str, Any]],
        csv_enabled: bool = True,
        json_enabled: bool = True,
    ) -> list[Path]:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created: list[Path] = []

        if csv_enabled:
            files_path = self.output_dir / f"relatorio_arquivos_{stamp}.csv"
            layers_path = self.output_dir / f"relatorio_camadas_{stamp}.csv"
            self._write_csv(files_path, file_rows)
            self._write_csv(layers_path, layer_rows)
            created.extend([files_path, layers_path])

        if json_enabled:
            json_path = self.output_dir / f"relatorio_completo_{stamp}.json"
            payload = {
                "resumo": summary.to_dict(),
                "arquivos": file_rows,
                "camadas": layer_rows,
            }
            json_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            created.append(json_path)
            latest = self.output_dir / "ultimo_relatorio.json"
            latest.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return created

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            path.write_text("sem_dados\n", encoding="utf-8-sig")
            return
        fieldnames: list[str] = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        with path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
