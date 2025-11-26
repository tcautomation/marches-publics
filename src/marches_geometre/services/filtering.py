# src/marches_geometre/services/filtering.py

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Set, Optional

from marches_geometre.models.tender import BoampNotice

# Mots-clés "métier" pour un cabinet de géomètre-expert
GEOMETER_KEYWORDS: List[str] = [
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

# Départements ciblés pour ton client (à ajuster si besoin)
TARGET_DEPARTMENTS: Set[str] = {"78", "92", "95"}


# ==========================
# Filtres géographiques & type de marché
# ==========================

def is_notice_in_target_departments(notice: BoampNotice) -> bool:
    """
    Vérifie si l'annonce est dans un des départements ciblés.

    - On prend le champ "department" tel qu'il est dans la notice.
    - Si c'est un code postal complet, on prend les 2 premiers chiffres.

    Dans notre mapping actuel, "department" vient de raw_fields["code_departement"].
    """
    if not notice.department:
        return False

    code = notice.department.strip()
    # Si c'est un code postal (5 chiffres), on garde les 2 premiers
    if len(code) >= 2 and code[:2].isdigit():
        code = code[:2]

    return code in TARGET_DEPARTMENTS


def is_notice_services_market(notice: BoampNotice) -> bool:
    """
    Vérifie que le type de marché correspond à "Services",
    comme dans le filtre du site BOAMP.

    On regarde à la fois :
    - raw_fields["type_marche"]   -> ex: "SERVICES"
    - raw_fields["type_marche_facette"] -> ex: "Services"

    Si l'un des deux contient "SERVICE", on considère que c'est ok.
    """
    fields = notice.raw_fields or {}

    type_marche = (fields.get("type_marche") or "").upper()
    type_marche_facette = (fields.get("type_marche_facette") or "").upper()

    if "SERVICE" in type_marche:
        return True
    if "SERVICE" in type_marche_facette:
        return True

    return False


# ==========================
# Filtres temporels (publication + AO en cours)
# ==========================

def _parse_date(value: Optional[str]) -> Optional[date]:
    """
    Parse une date provenant de BOAMP.

    Formats observés :
    - "YYYY-MM-DD"
    - "YYYY-MM-DDTHH:MM:SS+02:00"
    - éventuellement "...Z"

    On renvoie un objet date, ou None si impossible à parser.
    """
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    try:
        # Si la chaîne contient une partie horaire
        if "T" in value:
            # On remplace 'Z' par '+00:00' pour être compatible avec fromisoformat
            cleaned = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            return dt.date()
        # Sinon on prend simplement les 10 premiers caractères "YYYY-MM-DD"
        return date.fromisoformat(value[:10])
    except Exception:
        # En cas de format exotique, on ne casse pas tout
        return None


def is_notice_recent_and_open(notice: BoampNotice, days: int = 120) -> bool:
    """
    Vérifie deux conditions temporelles :

    1. La date de publication (dateparution) est dans les `days` derniers jours.
    2. La date limite de réponse (datelimitereponse) n'est pas encore passée
       (on considère l'AO "en cours" si date limite >= aujourd'hui).

    Si une des infos est manquante ou invalide -> False (par sécurité).
    """
    today = date.today()
    min_pub_date = today - timedelta(days=days)

    pub_date = _parse_date(notice.publication_date)
    if pub_date is None or pub_date < min_pub_date:
        return False

    deadline = _parse_date(notice.application_deadline)
    if deadline is None or deadline < today:
        return False

    return True
