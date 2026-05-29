from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.lotofacil.filters import (
    FilterConfig as LotofacilFilterConfig,
    default_filter_config as lotofacil_default,
)
from src.megasena.filters import (
    FilterConfig as MegasenaFilterConfig,
    default_filter_config as megasena_default,
)


def load_filter_config(config_path: Path, lottery_type: str = "lotofacil") -> Any:
    """
    Carrega a configuração de filtros apropriada para o tipo de loteria informado.
    """
    if not config_path.exists():
        if lottery_type == "megasena":
            cfg = megasena_default()
        else:
            cfg = lotofacil_default()
        save_filter_config(config_path, cfg)
        return cfg

    data = json.loads(config_path.read_text(encoding="utf-8"))
    
    if lottery_type == "megasena":
        return MegasenaFilterConfig(**data)
    else:
        return LotofacilFilterConfig(**data)


def save_filter_config(config_path: Path, cfg: Any) -> None:
    """
    Salva as configurações de qualquer dataclass de filtros de forma persistente em JSON.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
