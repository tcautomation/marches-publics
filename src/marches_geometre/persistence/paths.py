from pathlib import Path
from datetime import date

# Dossier racine du projet = dossier qui contient "data"
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # adapte à ta profondeur si besoin
DATA_DIR = PROJECT_ROOT / "data"

RAW_DIR = DATA_DIR / "raw"
RAW_AWS_DIR = RAW_DIR / "aws"
RAW_BOAMP_DIR = RAW_DIR / "boamp"
RAW_MAXIMILIEN_DIR = RAW_DIR / "maximilien"

PROCESSED_DIR = DATA_DIR / "processed"

for d in [RAW_DIR, RAW_AWS_DIR, RAW_BOAMP_DIR, RAW_MAXIMILIEN_DIR, PROCESSED_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def today_suffix(d: date | None = None) -> str:
    """
    Retourne la date au format YYYYMMDD pour suffixer les fichiers.
    """
    if d is None:
        d = date.today()
    return d.strftime("%Y%m%d")
