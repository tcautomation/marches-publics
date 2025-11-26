# run_pipeline.py
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import os


ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
SCRIPTS_DIR = ROOT / "scripts"
WEB_DIR = ROOT / "src" / "marches_geometre" / "web"
FINAL_JSON = WEB_DIR / "normalized_geometre_latest.json"


STEPS = [
    ("fetch_boamp", SCRIPTS_DIR / "fetch_boamp.py"),
    ("fetch_maximilien_geometre_idf", SCRIPTS_DIR / "fetch_maximilien_geometre_idf.py"),
    ("fetch_mp_info", SCRIPTS_DIR / "fetch_mp_info.py"),
    ("normalize_today", SCRIPTS_DIR / "normalize_today.py"),
    ("prepare_web_data", SCRIPTS_DIR / "prepare_web_data.py"),
]


def run_step(name: str, script_path: Path) -> None:
    print(f"\n=== Étape: {name} ===")
    print(f"-> python {script_path.relative_to(ROOT)}")

    # On part de l'env courant
    env = os.environ.copy()

    # On préfixe le PYTHONPATH avec src/
    existing = env.get("PYTHONPATH", "")
    new_pythonpath = str(SRC_DIR)
    if existing:
        new_pythonpath += os.pathsep + existing
    env["PYTHONPATH"] = new_pythonpath

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        env=env,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Échec de l'étape '{name}' (code retour={result.returncode}). "
            "Arrêt du pipeline."
        )


def main() -> None:
    print("============================================")
    print("  Pipeline veille marchés géomètre – IDF")
    print("============================================")
    print(f"Racine projet : {ROOT}")
    print(f"Date/heure    : {datetime.now().isoformat(timespec='seconds')}")

    for name, script in STEPS:
        run_step(name, script)

    if FINAL_JSON.is_file():
        print("\n✅ Pipeline terminé avec succès.")
        print(f"   Fichier final : {FINAL_JSON}")
    else:
        raise FileNotFoundError(f"Fichier final manquant : {FINAL_JSON}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n❌ ERREUR dans le pipeline :", e)
        sys.exit(1)
