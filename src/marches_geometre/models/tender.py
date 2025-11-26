# src/marches_geometre/models/tender.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


# =======================
# BOAMP
# =======================

@dataclass
class BoampNotice:
    """
    Représente une annonce BOAMP normalisée pour notre usage.
    """

    record_id: str
    title: Optional[str]
    reference: Optional[str]
    publication_date: Optional[str]
    buyer_name: Optional[str]
    department: Optional[str]
    city: Optional[str]
    postal_code: Optional[str]
    url: Optional[str]

    # Date limite de réponse brute renvoyée par l'API
    application_deadline: Optional[str]

    raw_fields: Dict[str, Any]

    @classmethod
    def from_record(cls, record: Dict[str, Any]) -> "BoampNotice":
        fields = record.get("fields", {})

        return cls(
            record_id=record.get("recordid", ""),
            title=fields.get("objet") or fields.get("intitule") or None,
            reference=fields.get("numeroad") or fields.get("idweb") or None,
            publication_date=fields.get("dateparution"),
            buyer_name=fields.get("nom_acheteur") or fields.get("nomacheteur"),
            department=str(fields.get("code_departement") or fields.get("departement") or ""),
            city=fields.get("ville"),
            postal_code=fields.get("code_postal") or fields.get("codepostal"),
            url=fields.get("lien") or fields.get("url") or fields.get("url_avis"),
            application_deadline=fields.get("datelimitereponse"),
            raw_fields=fields,
        )


# =======================
# Marches-publics.info (AWS)
# =======================

@dataclass
class AwsNotice:
    """
    Représente une annonce issue d'une page de résultats
    marches-publics.info (AWS).

    On reste volontairement texte + dates, c'est suffisant pour ton usage.
    """

    source: str  # "aws"
    category: Optional[str]          # ex: "SERVICES"
    publication_date: Optional[str]  # ex: "12/04/22"
    deadline_date: Optional[str]     # ex: "13/05/22"
    deadline_time: Optional[str]     # ex: "16h00"
    buyer_name: Optional[str]        # "VAL D'OISE HABITAT"
    buyer_code: Optional[str]        # "95031"
    reference: Optional[str]         # "AO GEOMETRE 2022"
    object: Optional[str]            # description du marché
    lots_info: Optional[str]         # ex: "[Marché alloti : 2 lots]"
    detail_url: Optional[str]        # URL complète "https://..."
    raw_html: str                    # bloc HTML brut pour debug

    estimated_budget: Optional[float] = None       # ex: 300000.0
    estimated_budget_raw: Optional[str] = None
