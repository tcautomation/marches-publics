# scripts/prepare_web_data.py

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("prepare_web_data")

DEDUPE_PATTERN = "normalized_geometre_deduped_*.json"
WEB_JSON_NAME = "normalized_geometre_latest.json"


def find_latest_deduped(processed_dir: Path) -> Optional[Path]:
    """
    Cherche le dernier fichier normalized_geometre_deduped_YYYYMMDD.json
    dans data/processed et renvoie son Path.
    """
    candidates = sorted(processed_dir.glob(DEDUPE_PATTERN))
    if not candidates:
        return None
    return candidates[-1]  # le plus récent alphabétiquement -> YYYYMMDD max


def main() -> None:
    base_dir = Path(__file__).resolve().parent.parent  # racine projet
    processed_dir = base_dir / "data" / "processed"
    web_dir = base_dir / "src" / "marches_geometre" / "web"

    logger.info("Répertoire processed : %s", processed_dir)
    logger.info("Répertoire web       : %s", web_dir)

    latest = find_latest_deduped(processed_dir)
    if latest is None:
        logger.error(
            "Aucun fichier '%s' trouvé dans %s",
            DEDUPE_PATTERN,
            processed_dir,
        )
        return

    logger.info("Dernier JSON dédoublonné trouvé : %s", latest.name)

    web_dir.mkdir(parents=True, exist_ok=True)
    dest = web_dir / WEB_JSON_NAME

    # On lit le JSON dédoublonné (qui est un tableau de notices)
    raw_content = latest.read_text(encoding="utf-8")
    try:
        notices = json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error("JSON invalide dans %s : %s", latest, e)
        return

    # Timestamp d'exécution du pipeline (UTC)
    generated_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "generated_at": generated_at,
        "notices": notices,
    }

    dest.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Fichier web écrit : %s", dest)
    logger.info("generated_at = %s", generated_at)
    logger.info("Terminée ✅")


if __name__ == "__main__":
    main()
