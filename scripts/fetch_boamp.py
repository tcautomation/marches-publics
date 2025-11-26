# scripts/fetch_boamp.py

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from marches_geometre.collectors.boamp_client import BoampClient
from marches_geometre.persistence.json_store import save_notices_to_json
from marches_geometre.services.filtering import (
    GEOMETER_KEYWORDS,
    is_notice_in_target_departments,
    is_notice_services_market,
    is_notice_recent_and_open,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("fetch_boamp")


def main() -> None:
    RAW_BOAMP_DIR = Path("data") / "raw" / "boamp"
    RAW_BOAMP_DIR.mkdir(parents=True, exist_ok=True)

    client = BoampClient()

    try:
        notices = client.search_notices(
            keywords=GEOMETER_KEYWORDS,
            max_records=1000,
            rows_per_page=100,
        )
    except RuntimeError as exc:
        logger.error("Impossible de récupérer les annonces BOAMP: %s", exc)
        return

    logger.info("Annonces récupérées avant filtres: %d", len(notices))

    services_notices = [n for n in notices if is_notice_services_market(n)]
    logger.info("Après filtre type de marché = Services: %d", len(services_notices))

    geo_filtered = [n for n in services_notices if is_notice_in_target_departments(n)]
    logger.info("Après filtre départements (78/92/95): %d", len(geo_filtered))

    recent_open = [n for n in geo_filtered if is_notice_recent_and_open(n, days=120)]
    logger.info(
        "Après filtre date + avis en cours: %d",
        len(recent_open),
    )

    today_str = datetime.now().strftime("%Y%m%d")
    output_path = RAW_BOAMP_DIR / f"boamp_geometre_{today_str}.json"

    try:
        save_notices_to_json(output_path, recent_open)
    except OSError:
        return

    logger.info("JSON BOAMP brut écrit dans: %s", output_path)


if __name__ == "__main__":
    main()
