# src/marches_geometre/services/normalization.py

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from marches_geometre.models.tender import BoampNotice, AwsNotice
from marches_geometre.models.normalized import NormalizedNotice
from marches_geometre.parsers.maximilien import MaximilienNotice

logger = logging.getLogger(__name__)

# =========================
# Helpers dates
# =========================


def _parse_iso_datetime(dt_str: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    BOAMP renvoie par ex : '2025-12-15T12:00:00+01:00'
    On extrait la date ISO (YYYY-MM-DD) et l'heure 'HH:MM'.
    """
    if not dt_str:
        return None, None

    try:
        dt = datetime.fromisoformat(dt_str)
    except ValueError:
        # on tente sans timezone au cas où
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            logger.warning("Impossible de parser la date BOAMP: %s", dt_str)
            return None, None

    date_iso = dt.date().isoformat()
    time_hm = dt.time().strftime("%H:%M")
    return date_iso, time_hm


def _parse_fr_date(d_str: Optional[str]) -> Optional[str]:
    """
    AWS : 'dd/mm/yy' -> 'YYYY-MM-DD'
    Exemple: '18/12/24' -> '2024-12-18'
    """
    if not d_str:
        return None

    try:
        dt = datetime.strptime(d_str, "%d/%m/%y")
    except ValueError:
        logger.warning("Impossible de parser la date AWS: %s", d_str)
        return None

    return dt.date().isoformat()


def _extract_department_from_locations(locations: Optional[List[str]]) -> Optional[str]:
    """
    Maximilien : les localisations ressemblent à '(92) Hauts-de-Seine ...'
    On essaye d'extraire le code département '92'.
    """
    if not locations:
        return None

    first = locations[0]
    if "(" in first and ")" in first:
        try:
            inside = first.split("(", 1)[1].split(")", 1)[0]
            code = inside.strip()
            # on ne garde que les 2 ou 3 premiers caractères numériques
            return "".join(ch for ch in code if ch.isdigit())[:3] or None
        except Exception:
            return None
    return None


# =========================
# Converters
# =========================


def normalize_boamp_notice(n: BoampNotice) -> NormalizedNotice:
    """
    Transforme un avis BOAMP en avis normalisé.
    """
    # Titre / description : on essaie d'avoir un intitulé + un objet
    title = n.title or n.raw_fields.get("objet")
    description = n.raw_fields.get("objet") or n.title

    # Date de publication est déjà en ISO (2025-11-19)
    publication_date = n.publication_date

    # Deadline : string ISO avec heure + timezone
    deadline_date, deadline_time = _parse_iso_datetime(n.application_deadline)

    # Identifiant pour la source : on privilégie idweb/ref s'il existe
    source_notice_id = n.reference or n.record_id

    return NormalizedNotice(
        source="boamp",
        source_notice_id=source_notice_id,
        reference=n.reference,
        title=title,
        description=description,
        buyer_name=n.buyer_name,
        department=n.department,
        city=n.city,
        postal_code=n.postal_code,
        publication_date=publication_date,
        deadline_date=deadline_date,
        deadline_time=deadline_time,
        url=n.url,
        estimated_budget=None,  # pas d'info budget dispo pour le moment
        extra={
            "type_marche": n.raw_fields.get("type_marche"),
            "descripteur_libelle": n.raw_fields.get("descripteur_libelle"),
            "etat": n.raw_fields.get("etat"),
        },
    )


def normalize_aws_notice(
    n: AwsNotice,
    *,
    department: Optional[str] = None,
) -> NormalizedNotice:
    """
    Transforme un avis AWS en avis normalisé.

    On peut passer 'department' car on le connaît via le filtre de recherche,
    mais il n'est pas explicite dans la page de résultats.
    """
    publication_date = _parse_fr_date(n.publication_date)
    deadline_date = _parse_fr_date(n.deadline_date)
    deadline_time = n.deadline_time

    # On n'a pas d'id "officiel" unique, on prend la référence comme identifiant.
    source_notice_id = n.reference or (n.detail_url or "")

    return NormalizedNotice(
        source="aws",
        source_notice_id=source_notice_id,
        reference=n.reference,
        title=n.object or n.reference,
        description=n.object,
        buyer_name=(n.buyer_name.strip() if n.buyer_name else None),
        department=department,
        city=None,             # pas dispo dans la liste
        postal_code=None,      # idem
        publication_date=publication_date,
        deadline_date=deadline_date,
        deadline_time=deadline_time,
        url=n.detail_url,
        estimated_budget=None,  # pas d'info fiable sur le prix dans la liste
        extra={
            "category": n.category,
            "lots_info": n.lots_info,
        },
    )


def normalize_maximilien_notice(n: MaximilienNotice) -> NormalizedNotice:
    """
    Transforme un avis Maximilien en avis normalisé.
    published_at et deadline peuvent être str OU datetime selon comment le JSON a été généré.
    """
    # --- Publication ---
    publication_date = None
    pub = getattr(n, "published_at", None)

    if isinstance(pub, datetime):
        publication_date = pub.date().isoformat()
    elif isinstance(pub, str):
        # normalement déjà ISO 'YYYY-MM-DD'
        publication_date = pub.strip()

    # --- Deadline ---
    deadline_date = None
    deadline_time = None
    dl = getattr(n, "deadline", None)

    if isinstance(dl, datetime):
        deadline_date = dl.date().isoformat()
        deadline_time = dl.time().strftime("%H:%M")
    elif isinstance(dl, str):
        # essaye format ISO standard : '2025-12-18T17:30:00'
        try:
            dt = datetime.fromisoformat(dl)
            deadline_date = dt.date().isoformat()
            deadline_time = dt.time().strftime("%H:%M")
        except Exception:
            # si jamais format inconnu on log mais on continue
            logger.warning("Impossible de parser deadline Maximilien: %s", dl)

    # --- Département ---
    department = _extract_department_from_locations(getattr(n, "locations", None))

    source_notice_id = getattr(n, "source_id", None) or getattr(n, "reference", None)

    return NormalizedNotice(
        source="maximilien",
        source_notice_id=source_notice_id,
        reference=getattr(n, "reference", None),
        title=getattr(n, "title", None),
        description=getattr(n, "object", None),
        buyer_name=getattr(n, "buyer", None),
        department=department,
        city=None,
        postal_code=None,
        publication_date=publication_date,
        deadline_date=deadline_date,
        deadline_time=deadline_time,
        url=getattr(n, "url", None),
        estimated_budget=None,
        extra={
            "procedure": getattr(n, "procedure", None),
            "category": getattr(n, "category", None),
            "raw_locations": getattr(n, "locations", None),
        },
    )


# =========================
# Chargement JSON (Maximilien)
# =========================


def load_maximilien_notices(path: Path) -> List[MaximilienNotice]:
    """
    Charge un fichier JSON Maximilien (liste de dicts) en liste de MaximilienNotice.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    return [MaximilienNotice(**item) for item in data]


# =========================
# Agrégateur
# =========================


def normalize_all(
    boamp_notices: List[BoampNotice],
    aws_notices: List[AwsNotice],
    maximilien_notices: Optional[List[MaximilienNotice]] = None,
    *,
    aws_department: Optional[str] = None,
) -> List[NormalizedNotice]:
    """
    Concatène les listes BOAMP + AWS (+ Maximilien) dans un seul flux normalisé.
    """
    normalized: List[NormalizedNotice] = []

    for n in boamp_notices:
        normalized.append(normalize_boamp_notice(n))

    for n in aws_notices:
        normalized.append(normalize_aws_notice(n, department=aws_department))

    if maximilien_notices:
        for n in maximilien_notices:
            normalized.append(normalize_maximilien_notice(n))

    logger.info(
        "Normalisation terminée : %d BOAMP + %d AWS + %d Maximilien -> %d avis",
        len(boamp_notices),
        len(aws_notices),
        len(maximilien_notices or []),
        len(normalized),
    )
    return normalized
