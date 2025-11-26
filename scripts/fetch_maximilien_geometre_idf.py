# scripts/fetch_maximilien_geometre_idf.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from marches_geometre.collectors.maximilien_client import (
    MaximilienClient,
    MaximilienSearchConfig,
)
from marches_geometre.parsers.maximilien import (
    parse_maximilien_search_results,
    MaximilienNotice,
)


logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def ensure_directories() -> Dict[str, Path]:
    base_raw = Path("data") / "raw" / "maximilien"
    base_raw.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    date_str = now.strftime("%Y%m%d")

    html_path = base_raw / f"maximilien_geometre_idf_{date_str}.html"
    json_path = base_raw / f"maximilien_geometre_idf_{date_str}.json"

    return {"html": html_path, "json": json_path}


def maximilien_notice_to_dict(n: MaximilienNotice) -> Dict[str, Any]:
    """Convertit un avis Maximilien en dict JSON-sérialisable."""
    return {
        "source": getattr(n, "source", "maximilien"),
        "source_id": getattr(n, "source_id", None),
        "reference": getattr(n, "reference", None),
        "title": getattr(n, "title", None),
        "object": getattr(n, "object", None),
        "buyer": getattr(n, "buyer", None),
        "procedure": getattr(n, "procedure", None),
        "category": getattr(n, "category", None),
        "locations": getattr(n, "locations", []),
        "published_at": (
            n.published_at.isoformat() if getattr(n, "published_at", None) else None
        ),
        "deadline": (
            n.deadline.isoformat() if getattr(n, "deadline", None) else None
        ),
        "url": getattr(n, "url", None),
    }


def main() -> None:
    setup_logging()
    paths = ensure_directories()

    logger.info("Lancement récupération Maximilien (géomètre IDF)...")

    search_config = MaximilienSearchConfig(
        days_back=180,
    )

    client = MaximilienClient()

    logger.info("Appel Maximilien (GET + POST)...")
    html = client.fetch_all_consultations_html(config=search_config)
    logger.info("HTML récupéré (%d caractères)", len(html))

    paths["html"].write_text(html, encoding="utf-8")
    logger.info("HTML sauvegardé dans %s", paths["html"])

    logger.info("Parsing des avis...")
    notices: List[MaximilienNotice] = parse_maximilien_search_results(html)
    logger.info("%d avis parsés depuis Maximilien", len(notices))

    if not notices:
        logger.warning("Aucun avis parsé, le JSON sera une liste vide []")
    else:
        # Debug : afficher le premier avis parsé
        first = notices[0]
        logger.info("Premier avis parsé (obj): %r", first)
        first_dict = maximilien_notice_to_dict(first)
        logger.info("Premier avis converti en dict: %s", first_dict)

    # Conversion en liste de dicts
    data = [maximilien_notice_to_dict(n) for n in notices]
    logger.info("Nombre d'entrées mises dans le JSON: %d", len(data))

    # Debug console (optionnel)
    if data:
        print("=== APERÇU DATA ===")
        print(json.dumps(data[0], ensure_ascii=False, indent=2))

    with paths["json"].open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info("JSON brut sauvegardé dans %s", paths["json"])
    logger.info("Terminé ✅")


if __name__ == "__main__":
    main()
