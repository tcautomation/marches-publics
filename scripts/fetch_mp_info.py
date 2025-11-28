# scripts/fetch_mp_info.py

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

# ----------------- Mots-clés géomètre -----------------

GEOMETER_KEYWORDS = [
    "géomètre",
    "géomètre-expert",
    "geometre",
    "geometre-expert",
    "topographie",
    "topographique",
    "bornage",
    "plan de division",
    "état descriptif de division",
    "etat descriptif de division",
    "EDD",
]


def main() -> None:
    RAW_AWS_DIR = Path("data") / "raw" / "aws"
    RAW_AWS_DIR.mkdir(parents=True, exist_ok=True)

    config = MpInfoSearchConfig(
        search_url="https://www.marches-publics.info/Annonces/lister",
    )
    client = MpInfoFormClient(config)

    # On agrège tous les résultats (tous départements x tous mots-clés)
    all_notices = []

    departments = ["92", "95", "78"]

    for dep in departments:
        for kw in GEOMETER_KEYWORDS:
            logger.info(
                "Recherche AWS (mp-info) - dep=%s | kw='%s' | status=en_cours | nature=services",
                dep,
                kw,
            )
            try:
                notices = client.search_notices(
                    status="en_cours",
                    nature="services",
                    department_code=dep,
                    keyword=kw,
                    enrich_with_detail=True,
                )
            except RuntimeError as exc:
                logger.error(
                    "Erreur lors de la récupération AWS/mpinfo pour dep=%s kw='%s' : %s",
                    dep,
                    kw,
                    exc,
                )
                continue

            logger.info(
                "→ %d annonces trouvées pour dep=%s, kw='%s'",
                len(notices),
                dep,
                kw,
            )
            all_notices.extend(notices)

    logger.info(
        "TOTAL annonces AWS récupérées (tous deps / mots-clés) : %d",
        len(all_notices),
    )

    today_str = datetime.now().strftime("%Y%m%d")
    # On garde volontairement le même nom de fichier pour ne rien casser ailleurs
    output_path = RAW_AWS_DIR / f"aws_geometre_expires_95_{today_str}.json"

    try:
        save_notices_to_json(output_path, all_notices)
    except OSError as exc:
        logger.error("Erreur lors de l'écriture du JSON AWS brut : %s", exc)
        return

    logger.info("JSON AWS brut écrit dans : %s", output_path)


if __name__ == "__main__":
    main()
