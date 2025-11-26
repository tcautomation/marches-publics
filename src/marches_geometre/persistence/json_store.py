# src/marches_geometre/persistence/json_store.py

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List

from marches_geometre.models.tender import BoampNotice

logger = logging.getLogger(__name__)


def save_notices_to_json(path: Path, notices: Iterable[BoampNotice]) -> None:
    """
    Sauvegarde une liste de BoampNotice dans un fichier JSON.

    - path : chemin du fichier de sortie
    - notices : itérable d'instances BoampNotice

    Le JSON contiendra une liste de dicts.
    """
    # On convertit les dataclasses BoampNotice en dicts
    notices_list: List[dict] = [asdict(n) for n in notices]

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(notices_list, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.error("Erreur lors de l'écriture du fichier JSON %s: %s", path, exc)
        raise
