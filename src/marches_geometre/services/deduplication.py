# src/marches_geometre/services/deduplication.py

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import replace
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from marches_geometre.models.normalized import NormalizedNotice

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
#   Priorité des sources pour choisir le "bon" avis
# ---------------------------------------------------------
SOURCE_PRIORITY = {
    "boamp": 3,
    "maximilien": 2,
    "aws": 1,
}

# ---------------------------------------------------------
#   NORMALISATION TEXTE
# ---------------------------------------------------------

def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def _normalize(s: Optional[str]) -> str:
    if not s:
        return ""
    s = _strip_accents(s.lower())
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())

def _canonical_url(url: Optional[str]) -> str:
    if not url:
        return ""
    url = url.strip()
    url = re.sub(r"#.*$", "", url)
    url = re.sub(r"\?.*$", "", url)
    return url

def _parse_date(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except:
        return None

def _date_close(d1: Optional[str], d2: Optional[str], tol: int = 3) -> bool:
    a = _parse_date(d1)
    b = _parse_date(d2)
    if not a or not b:
        return False
    return abs((a - b).days) <= tol

def _jaccard(a: str, b: str) -> float:
    A = set(_normalize(a).split())
    B = set(_normalize(b).split())
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)

# ---------------------------------------------------------
#   FUSION D'UN GROUPE
# ---------------------------------------------------------

def _choose_best(notices: List[NormalizedNotice]) -> NormalizedNotice:
    """ Choisit le meilleur avis du groupe (selon la source, puis la date). """
    def key(n: NormalizedNotice):
        return (
            SOURCE_PRIORITY.get(n.source, 0),
            n.publication_date or "",
        )
    return max(notices, key=key)

def _merge_group(group: List[NormalizedNotice]) -> NormalizedNotice:
    """ Fusionne un groupe en un seul avis (conservateur). """
    best = _choose_best(group)
    merged = replace(best)

    extra = dict(best.extra or {})
    extra["merged_sources"] = sorted({n.source for n in group})
    extra["other_urls"] = sorted({n.url for n in group if n.url != best.url})
    extra["other_refs"] = sorted({n.reference for n in group if n.reference != best.reference})

    merged.extra = extra
    return merged

# ---------------------------------------------------------
#   REGROUPEMENT SIMPLIFIÉ & PRUDENT
# ---------------------------------------------------------

def _soft_signature(n: NormalizedNotice) -> Tuple[str, str, str, str]:
    """ Clé prudente pour détecter un éventuel doublon cross-sources. """
    return (
        _normalize(n.title),
        _normalize(n.buyer_name),
        n.deadline_date or "",
        (n.department or "").strip(),
    )

def deduplicate_notices(notices: List[NormalizedNotice]) -> List[NormalizedNotice]:
    """
    Dédoublonnage TRÈS CONSERVATEUR :

    1) Dédoublonnage strict : même source + même source_notice_id.
    2) Regroupement par signature douce, mais uniquement si :
       - plusieurs SOURCES différentes
       - mêmes titre/acheteur/département/deadline
       - similarité titre >= 0.85
    3) Pas de fusion entre avis de la même source (BOAMP vs BOAMP = interdit).

    But : NE RIEN SUPPRIMER injustement.
    """

    if not notices:
        return []

    # ---------------------------------------------
    # 1) Dédoublonnage strict
    # ---------------------------------------------
    strict_dict = {}
    for n in notices:
        key = (n.source, n.source_notice_id)
        if key not in strict_dict:
            strict_dict[key] = n

    after_strict = list(strict_dict.values())
    logger.info("Dédoublonnage strict : %d -> %d", len(notices), len(after_strict))

    # ---------------------------------------------
    # 2) Groupement par signature douce (multi-source ONLY)
    # ---------------------------------------------
    buckets: Dict[Tuple[str, str, str, str], List[NormalizedNotice]] = {}
    for n in after_strict:
        sig = _soft_signature(n)
        # si le titre ou acheteur vide, ne pas fusionner
        if not sig[0] or not sig[1]:
            # clé unique => on ne fusionnera pas
            buckets.setdefault((f"unique_{id(n)}", "", "", ""), []).append(n)
        else:
            buckets.setdefault(sig, []).append(n)

    final = []

    for sig, group in buckets.items():

        if len(group) == 1:
            final.append(group[0])
            continue

        # vérifier si multi-sources
        sources = {n.source for n in group}
        if len(sources) == 1:
            # groupe homogène => surtout PAS de fusion.
            final.extend(group)
            continue

        # test de similarité
        base = group[0].title or ""
        ok = True
        for n in group[1:]:
            if _jaccard(base, n.title or "") < 0.85:
                ok = False
                break

        if not ok:
            final.extend(group)
            continue

        # Groupe réellement multi-sources cohérent → fusion prudente
        merged = _merge_group(group)
        final.append(merged)

    logger.info("Dédoublonnage final : %d -> %d", len(after_strict), len(final))
    return final
