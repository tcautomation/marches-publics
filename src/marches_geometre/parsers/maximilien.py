from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional
import re

from bs4 import BeautifulSoup


# ==========================
#   Utilitaires de dates
# ==========================

FRENCH_MONTHS = {
    # On couvre un max de variantes possibles
    "janv.": 1,
    "janvier": 1,
    "févr.": 2,
    "fév.": 2,
    "fevr.": 2,
    "février": 2,
    "mars": 3,
    "avr.": 4,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juil.": 7,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "sept.": 9,
    "septembre": 9,
    "oct.": 10,
    "octobre": 10,
    "nov.": 11,
    "novembre": 11,
    "déc.": 12,
    "décembre": 12,
    "dec.": 12,
    "decembre": 12,
}


def _parse_french_date(day_str: str, month_str: str, year_str: str) -> Optional[date]:
    """
    Convertit un triplet (jour, mois FR, année) en date Python.

    Exemple :
        "25", "Fév.", "2025" -> date(2025, 2, 25)
    """
    day_str = (day_str or "").strip()
    month_str = (month_str or "").strip().lower()
    year_str = (year_str or "").strip()

    if not day_str or not month_str or not year_str:
        return None

    # On nettoie un peu le mois
    month_str = month_str.replace("é", "é").replace("É", "é")
    key = month_str

    # On essaye avec/sans point
    if key not in FRENCH_MONTHS:
        key = key.rstrip(".")
        if key in FRENCH_MONTHS:
            month = FRENCH_MONTHS[key]
        else:
            key_dot = key + "."
            month = FRENCH_MONTHS.get(key_dot)
    else:
        month = FRENCH_MONTHS[key]

    if not month:
        return None

    try:
        return date(int(year_str), month, int(day_str))
    except ValueError:
        return None


def _parse_french_datetime(
    day: str,
    month: str,
    year: str,
    time_str: str,
) -> Optional[datetime]:
    """
    Combine une date FR + une heure "HH:MM" en datetime.
    """
    d = _parse_french_date(day, month, year)
    if not d:
        return None

    time_str = (time_str or "").strip()
    if not time_str:
        # Pas d'heure -> minuit
        return datetime(d.year, d.month, d.day)

    m = re.match(r"(\d{1,2}):(\d{2})", time_str)
    if not m:
        return datetime(d.year, d.month, d.day)

    hour = int(m.group(1))
    minute = int(m.group(2))

    try:
        return datetime(d.year, d.month, d.day, hour, minute)
    except ValueError:
        return datetime(d.year, d.month, d.day)


def _extract_source_id_from_url(url: str) -> Optional[str]:
    """
    Extrait l'ID consultation à partir d'une URL de type :
        /entreprise/consultation/903785?orgAcronyme=a0z
        https://marches.maximilien.fr/entreprise/consultation/903785?orgAcronyme=a0z
    """
    m = re.search(r"/consultation/(\d+)", url)
    if m:
        return m.group(1)
    return None


# ==========================
#   Modèle de notice
# ==========================

@dataclass
class MaximilienNotice:
    source: str               # "maximilien"
    source_id: str            # ID numérique dans l'URL
    reference: Optional[str]
    title: str
    object: Optional[str]
    buyer: Optional[str]
    procedure: Optional[str]
    category: Optional[str]
    locations: List[str]      # ex: ["(78) Yvelines", "(92) Hauts-de-Seine"]
    published_at: Optional[date]
    deadline: Optional[datetime]
    url: str                  # URL relative ou absolue vers la consultation


# ==========================
#   Parser principal
# ==========================

def parse_maximilien_search_results(html: str) -> List[MaximilienNotice]:
    """
    Parse la page de résultats de la recherche avancée Maximilien et
    renvoie une liste de MaximilienNotice.

    On suppose que le HTML vient d'une page de type :
        ?page=Entreprise.EntrepriseAdvancedSearch&searchAnnCons
        (après POST du formulaire)

    Points importants :
      - chaque consultation est dans un <div class="item_consultation list-group-item">
      - la colonne de droite contient la date limite (deadline)
      - la colonne centrale contient référence, intitulé, objet, organisme
      - la colonne de gauche contient procédure, catégorie, date de publication
    """
    soup = BeautifulSoup(html, "html.parser")

    notices: List[MaximilienNotice] = []

    rows = soup.select("div.item_consultation.list-group-item")
    for row in rows:
        # ==========================
        # URL & ID source
        # ==========================
        url = None
        actions_col = row.select_one("div.col_actions")
        if actions_col:
            for a in actions_col.find_all("a"):
                href = a.get("href", "")
                if "/entreprise/consultation/" in href:
                    url = href
                    break

        if not url:
            # Si on n'a pas d'URL, la notice est difficile à exploiter -> on skip
            continue

        source_id = _extract_source_id_from_url(url) or ""

        # ==========================
        # Procédure & catégorie
        # ==========================
        procedure = None
        proc_el = row.select_one(".cons_ref .cons_procedure span")
        if proc_el:
            procedure = proc_el.get_text(strip=True) or None

        category = None
        cat_el = row.select_one(".cons_ref .cons_categorie span")
        if cat_el:
            category = cat_el.get_text(strip=True) or None

        # ==========================
        # Date de publication
        # ==========================
        pub_day_el = row.select_one(".cons_ref .date-min .day span") or row.select_one(
            ".cons_ref .date .day span"
        )
        pub_month_el = row.select_one(".cons_ref .date-min .month span") or row.select_one(
            ".cons_ref .date .month span"
        )
        pub_year_el = row.select_one(".cons_ref .date-min .year span") or row.select_one(
            ".cons_ref .date .year span"
        )

        published_at: Optional[date] = None
        if pub_day_el and pub_month_el and pub_year_el:
            published_at = _parse_french_date(
                pub_day_el.get_text(),
                pub_month_el.get_text(),
                pub_year_el.get_text(),
            )

        # ==========================
        # Référence & titre
        # ==========================
        reference: Optional[str] = None
        title: str = ""

        objet_line = row.select_one(".cons_intitule .objet-line")
        if objet_line:
            # En général : deux div.small, 1 = référence, 2 = intitulé
            smalls = objet_line.select("div.small")
            if len(smalls) >= 1:
                ref_text = smalls[0].get_text(" ", strip=True)
                # Souvent "Référence de la consultation : 2025-1234"
                if ":" in ref_text:
                    ref_text = ref_text.split(":", 1)[1].strip()
                reference = ref_text or None

            if len(smalls) >= 2:
                span_title = smalls[1].find("span")
                if span_title:
                    title = (span_title.get("title") or span_title.get_text() or "").strip()

        # fallback si jamais pas d'intitulé
        if not title:
            title = reference or ""

        # ==========================
        # Objet
        # ==========================
        object_text: Optional[str] = None
        cons_intitule = row.select_one(".cons_intitule")
        if cons_intitule:
            # On cherche un div contenant "Objet :"
            for div in cons_intitule.find_all("div"):
                txt = div.get_text(" ", strip=True)
                if "Objet :" in txt:
                    # On récupère tout ce qui est après "Objet :"
                    object_text = txt.split("Objet :", 1)[1].strip() or None
                    break

        # ==========================
        # Organisme (acheteur)
        # ==========================
        buyer: Optional[str] = None
        if cons_intitule:
            for div in cons_intitule.find_all("div"):
                txt = div.get_text(" ", strip=True)
                if "Organisme :" in txt:
                    buyer = txt.split("Organisme :", 1)[1].strip() or None
                    break

        # ==========================
        # Lieux d'exécution
        # ==========================
        locations: List[str] = []
        lieux_block = row.select_one(".lieux-exe")
        if lieux_block:
            loc_text = lieux_block.get_text(" ", strip=True)
            # Souvent "Lieu d'exécution : (78) Yvelines, (92) Hauts-de-Seine"
            if ":" in loc_text:
                loc_text = loc_text.split(":", 1)[1]
            # On découpe sur les virgules
            for part in loc_text.split(","):
                p = part.strip()
                if p:
                    locations.append(p)

        # ==========================
        # Deadline (date limite)
        # ==========================
        d_day_el = row.select_one(".cons_dateEnd .cloture-line .date .day span") or row.select_one(
            ".cons_dateEnd .date .day span"
        )
        d_month_el = row.select_one(
            ".cons_dateEnd .cloture-line .date .month span"
        ) or row.select_one(".cons_dateEnd .date .month span")
        d_year_el = row.select_one(
            ".cons_dateEnd .cloture-line .date .year span"
        ) or row.select_one(".cons_dateEnd .date .year span")
        d_time_el = row.select_one(".cons_dateEnd .cloture-line .time label") or row.select_one(
            ".cons_dateEnd .time label"
        )

        deadline: Optional[datetime] = None
        if d_day_el and d_month_el and d_year_el:
            d_day = d_day_el.get_text()
            d_month = d_month_el.get_text()
            d_year = d_year_el.get_text()
            d_time = d_time_el.get_text() if d_time_el else ""
            deadline = _parse_french_datetime(d_day, d_month, d_year, d_time)

        # ==========================
        # Construction de la notice
        # ==========================
        notices.append(
            MaximilienNotice(
                source="maximilien",
                source_id=source_id,
                reference=reference,
                title=title,
                object=object_text,
                buyer=buyer,
                procedure=procedure,
                category=category,
                locations=locations,
                published_at=published_at,
                deadline=deadline,
                url=url,
            )
        )

    return notices


# Petit main de debug possible (à lancer manuellement si besoin)
if __name__ == "__main__":
    from pathlib import Path

    path = Path("data/raw/maximilien_all.html")
    if path.exists():
        html = path.read_text(encoding="utf-8")
        res = parse_maximilien_search_results(html)
        print(f"{len(res)} notices parsées")
        for n in res[:5]:
            print("----")
            print("ID       :", n.source_id)
            print("Ref      :", n.reference)
            print("Titre    :", n.title)
            print("Acheteur :", n.buyer)
            print("Proc     :", n.procedure, "| Catégorie:", n.category)
            print("Lieux    :", ", ".join(n.locations))
            print("Publi    :", n.published_at)
            print("Deadline :", n.deadline)
            print("URL      :", n.url)
    else:
        print("Fichier data/raw/maximilien_all.html introuvable pour le test local.")
