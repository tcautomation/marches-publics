# scripts/normalize_today.py

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List

from marches_geometre.models.tender import BoampNotice, AwsNotice
from marches_geometre.services.normalization import (
    normalize_all,
    load_maximilien_notices,
)
from marches_geometre.services.deduplication import deduplicate_notices

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("normalize")


# ============================================================
#                 LOADERS POUR LES SOURCES
# ============================================================

def load_boamp(path: Path) -> List[BoampNotice]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [BoampNotice(**item) for item in data]


def load_aws(path: Path) -> List[AwsNotice]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [AwsNotice(**item) for item in data]


# ============================================================
#                      MAIN PIPELINE
# ============================================================

def main() -> None:

    today_str = datetime.now().strftime("%Y%m%d")

    # ------------------------------
    #      FICHIERS SOURCE (raw)
    # ------------------------------
    boamp_path = Path("data/raw/boamp") / f"boamp_geometre_{today_str}.json"
    aws_path = Path("data/raw/aws") / f"aws_geometre_expires_95_{today_str}.json"
    maxi_path = Path("data/raw/maximilien") / f"maximilien_geometre_idf_{today_str}.json"

    # ------------------------------
    #     CHARGEMENT RAW JSON
    # ------------------------------
    boamp_notices = load_boamp(boamp_path) if boamp_path.exists() else []
    aws_notices = load_aws(aws_path) if aws_path.exists() else []
    maxi_notices = load_maximilien_notices(maxi_path) if maxi_path.exists() else []

    logger.info("=== Chargement ===")
    logger.info("BOAMP       : %d notices", len(boamp_notices))
    logger.info("AWS         : %d notices", len(aws_notices))
    logger.info("Maximilien  : %d notices", len(maxi_notices))

    # ------------------------------
    #           NORMALISATION
    # ------------------------------
    normalized = normalize_all(
        boamp_notices=boamp_notices,
        aws_notices=aws_notices,
        maximilien_notices=maxi_notices,
        aws_department="95",
    )

    logger.info("Normalisation : %d avis normalisés", len(normalized))

    # ------------------------------
    #        DEDOUBLONNAGE
    # ------------------------------
    deduped = deduplicate_notices(normalized)
    logger.info("Dédoublonnage : %d avis après fusion", len(deduped))

    # ------------------------------
    #      SAUVEGARDE FICHIERS
    # ------------------------------
    PROCESSED = Path("data") / "processed"
    PROCESSED.mkdir(parents=True, exist_ok=True)

    normalized_path = PROCESSED / f"normalized_geometre_{today_str}.json"
    deduped_path = PROCESSED / f"normalized_geometre_deduped_{today_str}.json"

    # version non dédupliquée
    normalized_path.write_text(
        json.dumps([asdict(n) for n in normalized], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # version dédupliquée
    deduped_path.write_text(
        json.dumps([asdict(n) for n in deduped], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("JSON normalisé écrit :  %s", normalized_path)
    logger.info("JSON dédoublonné écrit : %s", deduped_path)
    logger.info("Terminé ✓")


if __name__ == "__main__":
    main()
