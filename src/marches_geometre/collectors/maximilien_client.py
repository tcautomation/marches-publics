# src/marches_geometre/collectors/maximilien_client.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, Dict, Any

import logging
import requests
from requests import Response, Session
from requests.exceptions import RequestException, Timeout
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEARCH_URL = (
    "https://marches.maximilien.fr/"
    "?page=Entreprise.EntrepriseAdvancedSearch&searchAnnCons"
)


@dataclass
class MaximilienSearchConfig:
    """
    Paramètres de recherche pour Maximilien.

    Pour l'instant on hard-code ce qui t'intéresse (géomètre en IDF) :
    - Mots-clés dans le champ 'keywordSearch'
    - Catégorie = 3 (Services)
    - idsSelectedGeoN2 / numSelectedGeoN2 pour 78, 95, 92
    - days_back : nombre de jours de recul pour la date de mise en ligne
    """
    keywords: str = "geomètre geometre topographie bornage division EDD"
    # 3 = Services
    categorie: str = "3"
    # 78, 95, 92 -> codes N2 = 256, 261, 258 (valeurs vues dans le payload)
    ids_selected_geo_n2: str = ",,256,261,258,"
    num_selected_geo_n2: str = "78_95_92"
    # Nombre de jours de recul pour la date de mise en ligne
    days_back: int = 180


class MaximilienClient:
    """
    Client HTTP pour la recherche d'avis sur Maximilien.

    Important :
    - Utilise une Session pour garder les cookies entre GET et POST.
    - Récupère PRADO_PAGESTATE dynamiquement avant de poster.
    - Gère les timeouts et erreurs réseau avec des RuntimeError explicites.
    """

    def __init__(self, timeout: int = 30) -> None:
        self.session: Session = requests.Session()
        self.timeout = timeout

    # -----------------------
    #  Helpers internes HTTP
    # -----------------------

    def _get(self, url: str, **kwargs: Any) -> Response:
        """
        Wrapper GET avec gestion des erreurs réseau / timeout.
        """
        try:
            resp = self.session.get(url, timeout=self.timeout, **kwargs)
        except Timeout as exc:
            logger.error("Timeout lors de l'appel GET vers %s", url)
            raise RuntimeError(f"Timeout lors de l'appel GET vers {url}") from exc
        except RequestException as exc:
            logger.error("Erreur réseau lors de l'appel GET vers %s: %s", url, exc)
            raise RuntimeError(f"Erreur réseau lors de l'appel GET vers {url}") from exc

        if not resp.ok:
            logger.error(
                "Erreur HTTP GET Maximilien: url=%s status=%s body=%s",
                url,
                resp.status_code,
                resp.text[:500],
            )
            raise RuntimeError(f"Erreur HTTP GET Maximilien {resp.status_code}")

        return resp

    def _post(self, url: str, data: Dict[str, Any], headers: Dict[str, str]) -> Response:
        """
        Wrapper POST avec gestion des erreurs réseau / timeout.
        """
        try:
            resp = self.session.post(
                url,
                data=data,
                headers=headers,
                timeout=self.timeout,
            )
        except Timeout as exc:
            logger.error("Timeout lors de l'appel POST vers %s", url)
            raise RuntimeError(f"Timeout lors de l'appel POST vers {url}") from exc
        except RequestException as exc:
            logger.error("Erreur réseau lors de l'appel POST vers %s: %s", url, exc)
            raise RuntimeError(f"Erreur réseau lors de l'appel POST vers {url}") from exc

        if not resp.ok:
            logger.error(
                "Erreur HTTP POST Maximilien: url=%s status=%s body=%s",
                url,
                resp.status_code,
                resp.text[:500],
            )
            raise RuntimeError(f"Erreur HTTP POST Maximilien {resp.status_code}")

        return resp

    # -----------------------
    #  Helpers métier
    # -----------------------

    def _get_page_state(self) -> str:
        """
        Fait un GET sur la page de recherche avancée et extrait PRADO_PAGESTATE.

        Retourne :
            la valeur du champ caché PRADO_PAGESTATE.

        Lève une RuntimeError si le champ n'est pas trouvé.
        """
        logger.info("Récupération de PRADO_PAGESTATE sur la page de recherche Maximilien...")
        resp = self._get(SEARCH_URL)

        soup = BeautifulSoup(resp.text, "html.parser")
        hidden = soup.find("input", {"name": "PRADO_PAGESTATE"})
        if not hidden or not hidden.get("value"):
            logger.error("Impossible de trouver PRADO_PAGESTATE dans la page HTML Maximilien.")
            raise RuntimeError("Impossible de trouver PRADO_PAGESTATE dans la page de recherche Maximilien")

        page_state = hidden["value"]
        logger.debug("PRADO_PAGESTATE length=%d", len(page_state))
        return page_state

    @staticmethod
    def _format_french_date(d: date) -> str:
        """
        Retourne une date au format jj/mm/aaaa pour le formulaire Maximilien.
        """
        return d.strftime("%d/%m/%Y")

    # -----------------------
    #  API publique
    # -----------------------

    def search_geometre_idf_html(
        self,
        config: Optional[MaximilienSearchConfig] = None,
    ) -> str:
        """
        Exécute une recherche 'géomètre' sur Maximilien IDF
        et renvoie le HTML brut de la page de résultats.

        - Utilise la config pour :
          * les mots-clés
          * la catégorie (services)
          * les départements (78 / 92 / 95)
          * la fenêtre de date (days_back)
        """
        if config is None:
            config = MaximilienSearchConfig()

        # Sécurisation de days_back (on évite les valeurs absurdes ou négatives)
        days_back = config.days_back
        if days_back <= 0:
            logger.warning(
                "config.days_back=%s invalide, utilisation de 180 jours par défaut.",
                days_back,
            )
            days_back = 180

        logger.info(
            "Recherche Maximilien: keywords='%s', categorie=%s, zones=%s, days_back=%s",
            config.keywords,
            config.categorie,
            config.num_selected_geo_n2,
            days_back,
        )

        page_state = self._get_page_state()

        today = date.today()
        start_date = today - timedelta(days=days_back)

        date_start_str = self._format_french_date(start_date)
        date_end_str = self._format_french_date(today)

        payload: Dict[str, Any] = {
            "ctl0$CONTENU_PAGE$AdvancedSearch$keywordSearch": config.keywords,
            "ctl0$CONTENU_PAGE$AdvancedSearch$categorie": config.categorie,
            "ctl0$CONTENU_PAGE$AdvancedSearch$idsSelectedGeoN2": config.ids_selected_geo_n2,
            "ctl0$CONTENU_PAGE$AdvancedSearch$numSelectedGeoN2": config.num_selected_geo_n2,
            # Ne récupérer que les avis non clôturés
            "ctl0$CONTENU_PAGE$AdvancedSearch$affichageAlerteNonCloturee": "on",
            # Fenêtre de date calculée (vue dans le payload)
            "ctl0$CONTENU_PAGE$AdvancedSearch$dateMiseEnLigneCalculeStart": date_start_str,
            "ctl0$CONTENU_PAGE$AdvancedSearch$dateMiseEnLigneCalculeEnd": date_end_str,
            # Bouton de recherche
            "ctl0$CONTENU_PAGE$AdvancedSearch$lancerRecherche": "Lancer la recherche",
            # Champs PRADO obligatoires
            "PRADO_PAGESTATE": page_state,
            "PRADO_POSTBACK_TARGET": "ctl0$CONTENU_PAGE$AdvancedSearch$lancerRecherche",
        }

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0 Safari/537.36"
            ),
            "Referer": SEARCH_URL,
        }

        logger.info("Envoi du POST de recherche Maximilien...")
        resp = self._post(SEARCH_URL, data=payload, headers=headers)
        logger.info("HTML résultats Maximilien récupéré (%d caractères)", len(resp.text))

        return resp.text

    def fetch_all_consultations_html(
        self,
        config: Optional[MaximilienSearchConfig] = None,
    ) -> str:
        """
        Alias pour compatibilité avec l’ancien script.

        Pour l’instant : même chose que search_geometre_idf_html().
        """
        return self.search_geometre_idf_html(config)
