# src/marches_geometre/models/normalized.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any


SourceType = Literal["boamp", "aws"]


@dataclass
class NormalizedNotice:
    """
    Représentation commune d'un avis de marché (BOAMP, AWS...).
    """

    # Source du flux
    source: SourceType
    source_notice_id: str

    # Infos principales
    reference: Optional[str]
    title: Optional[str]
    description: Optional[str]

    buyer_name: Optional[str]
    department: Optional[str]
    city: Optional[str]
    postal_code: Optional[str]

    # Dates ISO
    publication_date: Optional[str]
    deadline_date: Optional[str]
    deadline_time: Optional[str]

    # URL de détail
    url: Optional[str]

    # Champs supplémentaires (facultatifs)
    extra: Dict[str, Any]

    # ➕ On rend le budget optionnel avec valeur par défaut
    estimated_budget: Optional[float] = None
    estimated_budget_raw: Optional[str] = None
