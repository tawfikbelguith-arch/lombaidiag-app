"""
Connexion Google Sheets (compte de service) pour enregistrer chaque analyse.

Prérequis :
- backend/credentials.json  (clé JSON du compte de service Google)
- La feuille Google Sheet doit être partagée en "Éditeur" avec l'adresse
  "client_email" contenue dans credentials.json
- Variable d'environnement SHEET_ID (ou modifier SHEET_ID ci-dessous)
"""

import os
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "credentials.json")
SHEET_ID = os.environ.get("LOMBAI_SHEET_ID", "1J6Nfxg1LX_JPZ_7-8sMCSwAuTzLaMU5U_lpyV-LrfoA")
WORKSHEET_NAME = "Feuille 1"  # nom de l'onglet dans votre Google Sheet

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client = None
_worksheet = None


def _get_worksheet():
    """Ouvre (et met en cache) la connexion à la feuille Google Sheets."""
    global _client, _worksheet
    if _worksheet is not None:
        return _worksheet

    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(
            f"Fichier credentials.json introuvable à {CREDENTIALS_PATH}. "
            "Voir les instructions de configuration Google Sheets."
        )

    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=_SCOPES)
    _client = gspread.authorize(creds)
    spreadsheet = _client.open_by_key(SHEET_ID)
    _worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    return _worksheet


def save_analysis(
    nom_patient: str,
    rapport: str,
    email: Optional[str] = None,
    whatsapp: Optional[str] = None,
) -> None:
    """
    Ajoute une ligne dans Google Sheets pour une analyse terminée.

    - nom_patient : nom saisi par le patient
    - rapport     : résumé du rapport (texte, ou lien vers le PDF)
    - email       : email du patient (peut être vide)
    - whatsapp    : numéro WhatsApp du patient (peut être vide)
    """
    try:
        worksheet = _get_worksheet()
        date_heure = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.append_row(
            [nom_patient or "", email or "", whatsapp or "", date_heure, rapport or ""],
            value_input_option="USER_ENTERED",
        )
    except Exception as exc:
        # On ne bloque jamais l'analyse IRM si Google Sheets échoue :
        # on logue simplement l'erreur côté serveur.
        print(f"[sheets.py] Erreur d'enregistrement Google Sheets : {exc}")