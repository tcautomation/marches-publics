# scripts/prepare_web_data.py

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

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

    content = latest.read_text(encoding="utf-8")
    dest.write_text(content, encoding="utf-8")

    logger.info("Copie effectuée vers : %s", dest)
    logger.info("Terminée ✅")


if __name__ == "__main__":
    main()
