# scripts/fetch_marches_publics_info.py

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from marches_geometre.collectors.mpinfo_form_client import (
    MpInfoFormClient,
    MpInfoSearchConfig,
)
from marches_geometre.persistence.json_store import save_notices_to_json

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("fetch_mpinfo")


def main() -> None:
    RAW_AWS_DIR = Path("data") / "raw" / "aws"
    RAW_AWS_DIR.mkdir(parents=True, exist_ok=True)

    config = MpInfoSearchConfig(
        search_url="https://www.marches-publics.info/Annonces/lister",
    )
    client = MpInfoFormClient(config)

    try:
        notices = client.search_notices(
            status="expires",
            nature="services",
            department_code="95",
            keyword="geomètre",
            enrich_with_detail=True,
        )
    except RuntimeError as exc:
        logger.error("Erreur lors de la récupération AWS/mpinfo: %s", exc)
        return

    logger.info("Nombre d'annonces AWS récupérées: %d", len(notices))

    today_str = datetime.now().strftime("%Y%m%d")
    output_path = RAW_AWS_DIR / f"aws_geometre_expires_95_{today_str}.json"

    try:
        save_notices_to_json(output_path, notices)
    except OSError:
        return

    logger.info("JSON AWS brut écrit dans : %s", output_path)


if __name__ == "__main__":
    main()
