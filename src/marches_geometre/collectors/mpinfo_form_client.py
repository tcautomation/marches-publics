# src/marches_geometre/collectors/mpinfo_form_client.py
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

import requests
from bs4 import BeautifulSoup
from requests import Session, Response
from requests.exceptions import RequestException, Timeout

from marches_geometre.models.tender import AwsNotice

logger = logging.getLogger(__name__)

AnnonceStatus = Literal["en_cours", "expires", "attributions", "donnees_essentielles"]
NatureType = Literal["toutes", "travaux", "services", "fournitures"]


# =====================================================
#                   CONFIG
# =====================================================

@dataclass
class MpInfoSearchConfig:
    """
    Configuration pour Marches-Publics.info (AWS).
    """

    search_url: str = "https://www.marches-publics.info/Annonces/lister"
    timeout: int = 15
    retries: int = 2                   # nombre de retries sur timeout


# =====================================================
#                   CLIENT
# =====================================================

class MpInfoFormClient:
    """
    Client qui :
    - soumet un POST au moteur de recherche AWS,
    - parse la page de résultats,
    - (optionnel) scrappe les pages de détail pour extraire un budget.
    """

    def __init__(self, config: Optional[MpInfoSearchConfig] = None):
        self.config = config or MpInfoSearchConfig()
        self.session: Session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; marches-geometre-bot/1.0; "
                    "+https://example.com/contact)"
                ),
                "Referer": "https://www.marches-publics.info/Annonces/rechercher",
            }
        )

    # ================================================
    #             HELPERS HTTP ROBUSTES
    # ================================================

    def _post(self, url: str, data: Dict[str, Any]) -> Response:
        """
        Enveloppe POST avec retry + logs + exceptions propres.
        """
        for attempt in range(self.config.retries + 1):
            try:
                resp = self.session.post(
                    url,
                    data=data,
                    timeout=self.config.timeout,
                )
                if resp.ok:
                    return resp

                logger.warning(
                    "HTTP %s sur %s (tentative %d/%d)",
                    resp.status_code,
                    url,
                    attempt + 1,
                    self.config.retries + 1,
                )

            except (Timeout, RequestException) as exc:
                logger.warning(
                    "Erreur réseau POST %s (tentative %d/%d): %s",
                    url,
                    attempt + 1,
                    self.config.retries + 1,
                    exc,
                )
                time.sleep(1.0)

        raise RuntimeError(f"Échec POST vers {url} après plusieurs tentatives.")

    def _get(self, url: str) -> Response:
        """
        Enveloppe GET avec retry.
        """
        for attempt in range(self.config.retries + 1):
            try:
                resp = self.session.get(url, timeout=self.config.timeout)
                if resp.ok:
                    return resp

                logger.warning(
                    "HTTP %s sur GET %s (tentative %d/%d)",
                    resp.status_code,
                    url,
                    attempt + 1,
                    self.config.retries + 1,
                )
            except (Timeout, RequestException) as exc:
                logger.warning(
                    "Erreur réseau GET %s (tentative %d/%d): %s",
                    url,
                    attempt + 1,
                    self.config.retries + 1,
                    exc,
                )
                time.sleep(1.0)

        raise RuntimeError(f"Échec GET {url} après plusieurs tentatives.")

    # ================================================
    #         BUILD FORM DATA POUR LE POST
    # ================================================

    def _build_form_data(
        self,
        status: AnnonceStatus,
        nature: NatureType,
        department_code: str,
        keyword: str,
    ) -> Dict[str, Any]:

        status_map = {
            "en_cours": "EC",
            "expires": "A",
            "attributions": "AAA",
            "donnees_essentielles": "DE",
        }

        nature_map = {
            "toutes": "X",
            "travaux": "T",
            "services": "S",
            "fournitures": "F",
        }

        if status not in status_map:
            raise ValueError(f"Status invalide: {status}")

        if nature not in nature_map:
            raise ValueError(f"Nature invalide: {nature}")

        form = {
            "IDE": status_map[status],
            "IDN": nature_map[nature],
            "IDP": "X",
            "IDR": department_code,
            "listeCPV": "",
            "txtLibre": keyword or "",
            "txtLibreLieuExec": "",
            "txtAcheteurNom": "",
            "txtAcheteurSiret": "",
            "txtTitulaireNom": "",
            "txtTitulaireSiret": "",
            "txtLibreAcheteur": "",
            "txtLibreVille": "",
            "txtLibreRef": "",
            "txtLibreObjet": "",
            "dateParution": "",
            "dateExpiration": "",
            "annee": "X",
            "Rechercher": "Rechercher",
        }

        return form

    # ================================================
    #                MAIN SEARCH
    # ================================================

    def search_html(
        self,
        status: AnnonceStatus,
        nature: NatureType,
        department_code: str,
        keyword: str,
    ) -> str:

        form_data = self._build_form_data(
            status=status,
            nature=nature,
            department_code=department_code,
            keyword=keyword,
        )

        logger.info(
            "POST AWS → %s | dép=%s | kw='%s' | status=%s | nature=%s",
            self.config.search_url,
            department_code,
            keyword,
            status,
            nature,
        )
        logger.debug("Payload envoyé : %s", form_data)

        resp = self._post(self.config.search_url, form_data)
        logger.info("HTML résultats AWS récupéré (%d caractères)", len(resp.text))
        return resp.text

    # ================================================
    #              PARSING HTML → AwsNotice
    # ================================================

    @staticmethod
    def _parse_notices_from_html(html: str) -> List[AwsNotice]:
        soup = BeautifulSoup(html, "html.parser")

        # onglet SERVICES (id=2)
        services_tab = soup.find("div", {"id": "2"}) or soup

        notices: List[AwsNotice] = []

        entities = services_tab.find_all("div", id="entity")
        if not entities:
            logger.warning("Aucune balise <div id='entity'> trouvée.")
            return []

        for entity in entities:
            raw_html = str(entity)

            # ------------------------------------
            #   Dates
            # ------------------------------------
            pub_date = None
            deadline_date = None
            deadline_time = None

            date_row = entity.find("div", class_="affiche_date_avis")
            if date_row:
                text = " ".join(date_row.stripped_strings)
                m_pub = re.search(r"Publié le\s+(\d{2}/\d{2}/\d{2})", text)
                m_dead = re.search(r"(\d{2}/\d{2}/\d{2})", text)
                m_time = re.search(r"(\d{2}h\d{2})", text)

                if m_pub:
                    pub_date = m_pub.group(1)
                if m_dead:
                    deadline_date = m_dead.group(1)
                if m_time:
                    deadline_time = m_time.group(1)

            # ------------------------------------
            #   Acheteur
            # ------------------------------------
            buyer_name = None
            buyer_code = None

            h2 = entity.find("h2", class_="h2-avis")
            if h2:
                line = " ".join(h2.stripped_strings)
                mm = re.match(r"^(.*)\((\d+)\)\s*$", line)
                if mm:
                    buyer_name = mm.group(1).strip()
                    buyer_code = mm.group(2)
                else:
                    buyer_name = line.strip()

            # ------------------------------------
            #   Référence + objet
            # ------------------------------------
            reference = None
            object_text = None
            lots_info = None

            titre_box = entity.find("div", id="titre_box")
            if titre_box:
                # référence
                ref_div = titre_box.find("div", class_="ref-acheteur")
                if ref_div:
                    txt = " ".join(ref_div.stripped_strings)
                    mm = re.search(r"\[réf\.\s*(.+?)\]", txt, flags=re.IGNORECASE)
                    reference = mm.group(1).strip() if mm else txt.strip()

                # lots
                p_lots = titre_box.find("p")
                if p_lots:
                    lots_info = " ".join(p_lots.stripped_strings)

                # objet
                full = " ".join(titre_box.stripped_strings)
                if ref_div:
                    full = full.replace(" ".join(ref_div.stripped_strings), "")
                if lots_info:
                    full = full.replace(lots_info, "")

                object_text = full.strip() or None

            # ------------------------------------
            #   URL détail
            # ------------------------------------
            detail_url = None
            link = entity.find("a", href=True, string=lambda s: s and "Consulter" in s)
            if link:
                href = link["href"]
                if href.startswith("http"):
                    detail_url = href
                else:
                    detail_url = "https://www.marches-publics.info" + href

            notices.append(
                AwsNotice(
                    source="aws",
                    category="SERVICES",
                    publication_date=pub_date,
                    deadline_date=deadline_date,
                    deadline_time=deadline_time,
                    buyer_name=buyer_name,
                    buyer_code=buyer_code,
                    reference=reference,
                    object=object_text,
                    lots_info=lots_info,
                    detail_url=detail_url,
                    raw_html=raw_html,
                )
            )

        logger.info("AWS : %d avis trouvés", len(notices))
        return notices

    # ================================================
    #        SCRAPPING PAGES DE DÉTAIL (BUDGET)
    # ================================================

    def _extract_budget_from_detail_html(self, html: str) -> tuple[Optional[float], Optional[str]]:
        text = " ".join(BeautifulSoup(html, "html.parser").stripped_strings)

        m = re.search(r"Montant HT\s*:?\s*([\d\s\u00A0\.,]+)\s*€", text, flags=re.IGNORECASE)
        if not m:
            return None, None

        raw = m.group(1).strip()
        cleaned = raw.replace("\u00A0", " ").replace(" ", "").replace(".", "")
        cleaned = cleaned.replace(",", ".")
        try:
            value = float(cleaned)
        except ValueError:
            return None, raw

        return value, raw

    def _enrich_notices_with_budget(self, notices: List[AwsNotice], sleep_seconds: float = 0.5) -> None:
        for n in notices:
            if not n.detail_url:
                continue

            try:
                resp = self._get(n.detail_url)
            except RuntimeError:
                continue

            budget_val, budget_raw = self._extract_budget_from_detail_html(resp.text)
            n.estimated_budget = budget_val
            n.estimated_budget_raw = budget_raw

            time.sleep(sleep_seconds)

    # ================================================
    #                   API PUBLIQUE
    # ================================================

    def search_notices(
        self,
        status: AnnonceStatus,
        nature: NatureType,
        department_code: str,
        keyword: str,
        enrich_with_detail: bool = False,
    ) -> List[AwsNotice]:

        html = self.search_html(
            status=status,
            nature=nature,
            department_code=department_code,
            keyword=keyword,
        )

        notices = self._parse_notices_from_html(html)

        if enrich_with_detail and notices:
            self._enrich_notices_with_budget(notices)

        return notices
