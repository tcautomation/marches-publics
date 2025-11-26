# src/marches_geometre/collectors/boamp_client.py

from __future__ import annotations

import logging
from typing import Any, Dict, List

import requests
from requests import Response, Session
from requests.exceptions import RequestException, Timeout

from marches_geometre.models.tender import BoampNotice

logger = logging.getLogger(__name__)

# Endpoint Opendatasoft pour BOAMP
BOAMP_API_URL = "https://boamp-datadila.opendatasoft.com/api/records/1.0/search/"
BOAMP_DATASET_ID = "boamp"


def build_query_string(keywords: List[str]) -> str:
    """
    Construit la chaîne de recherche 'q' pour Opendatasoft.

    Exemple : ["géomètre", "topographie"] -> "géomètre OR topographie"
    """
    unique_keywords = sorted(set(k.strip() for k in keywords if k.strip()))
    if not unique_keywords:
        raise ValueError("La liste de mots-clés pour la requête BOAMP est vide.")
    return " OR ".join(unique_keywords)


class BoampClient:
    """
    Client minimal pour interroger l'API BOAMP via Opendatasoft.
    """

    def __init__(self, base_url: str = BOAMP_API_URL, dataset_id: str = BOAMP_DATASET_ID):
        self.base_url = base_url
        self.dataset_id = dataset_id
        self.session: Session = requests.Session()
        # Timeout raisonnable pour éviter de bloquer le script
        self.timeout = 10

    def _request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envoie une requête GET à l'API avec gestion d'erreurs.

        Retourne le JSON décodé, ou lève une RuntimeError explicite.
        """
        try:
            response: Response = self.session.get(
                self.base_url,
                params=params,
                timeout=self.timeout,
            )
        except Timeout as exc:
            logger.error("Timeout lors de l'appel à l'API BOAMP.")
            raise RuntimeError("Timeout API BOAMP") from exc
        except RequestException as exc:
            logger.error("Erreur réseau lors de l'appel à l'API BOAMP: %s", exc)
            raise RuntimeError("Erreur réseau API BOAMP") from exc

        if not response.ok:
            logger.error(
                "Erreur HTTP BOAMP: status=%s, body=%s",
                response.status_code,
                response.text[:500],
            )
            raise RuntimeError(f"Erreur HTTP BOAMP {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("Réponse BOAMP non JSON: %s", response.text[:500])
            raise RuntimeError("Réponse BOAMP non JSON") from exc

        return data

    def search_notices(
        self,
        keywords: List[str],
        max_records: int = 200,
        rows_per_page: int = 50,
    ) -> List[BoampNotice]:
        """
        Récupère des annonces BOAMP contenant les mots-clés spécifiés.

        - keywords : liste de mots-clés pour "q"
        - max_records : nombre max d'annonces (pour éviter de tout aspirer)
        - rows_per_page : taille des pages de résultats

        Retourne une liste de BoampNotice normalisées.
        """
        query = build_query_string(keywords)
        logger.info("Requête BOAMP avec q=%s", query)

        notices: List[BoampNotice] = []
        start = 0

        while len(notices) < max_records:
            rows = min(rows_per_page, max_records - len(notices))

            params = {
                "dataset": self.dataset_id,
                "q": query,
                "rows": rows,
                "start": start,
                # ⚠️ IMPORTANT : tri décroissant (plus récents d'abord)
                # Sur Opendatasoft v1, 'sort=champ' = décroissant, '-champ' = croissant.
                "sort": "dateparution",
                "timezone": "Europe/Paris",
                "lang": "fr",
            }

            logger.info("Appel API BOAMP: start=%d, rows=%d", start, rows)
            data = self._request(params)

            records = data.get("records", [])
            if not records:
                logger.info("Plus aucun enregistrement retourné par l'API BOAMP, arrêt.")
                break

            for record in records:
                notice = BoampNotice.from_record(record)
                notices.append(notice)

                if len(notices) >= max_records:
                    break

            start += rows

        logger.info("Nombre total d'annonces récupérées (toutes dates confondues): %d", len(notices))
        return notices
