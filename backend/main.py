"""
main.py
-------
API FastAPI pour l'application d'aide au diagnostic de la lombalgie.
Reçoit une IRM + une référence patient, lance la segmentation, puis
retourne les images annotées, les métriques et les scores de risque.

Lancer avec :
    uvicorn main:app --reload
"""

import base64
import io
import os
import sys
import uuid
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

try:
    import SimpleITK as sitk
except ImportError:  # pragma: no cover - optional dependency
    sitk = None

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sheets import save_analysis
from report import generate_pdf_report
from segmentation import run_segmentation

app = FastAPI(title="API - Aide au diagnostic de la lombalgie")

DISCLAIMER = (
    "Ce résultat provient d'un pipeline de démonstration (traitement d'image "
    "classique) sans valeur diagnostique. Il ne remplace en aucun cas l'avis "
    "d'un professionnel de santé."
)

# Stockage en mémoire des résultats de session, le temps de générer le rapport PDF.
# À remplacer par une vraie persistance (DB / storage) en production.
SESSIONS: dict = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://lombaidiag.netlify.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _encode_png_data_uri(image_bgr_or_gray: np.ndarray) -> tuple[bytes, str]:
    """Encode une image OpenCV en PNG et retourne (bytes, data URI base64)."""
    ok, buf = cv2.imencode(".png", image_bgr_or_gray)
    if not ok:
        raise HTTPException(status_code=500, detail="Échec de l'encodage d'une image.")
    png_bytes = buf.tobytes()
    data_uri = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
    return png_bytes, data_uri


def load_image_from_upload_bytes(content: bytes, filename: str) -> np.ndarray:
    """Charge une image depuis des octets, y compris les formats MHA/MHD si SimpleITK est installé."""
    filename_lower = (filename or "").lower()

    if sitk is not None and filename_lower.endswith((".mha", ".mhd")):
        try:
            with io.BytesIO(content) as stream:
                image = sitk.ReadImage(stream)
            array = sitk.GetArrayFromImage(image)
            if array.ndim == 2:
                array = array[..., np.newaxis]
            if array.ndim == 3 and array.shape[0] == 1:
                array = np.repeat(array, 3, axis=0).transpose(1, 2, 0)
            elif array.ndim == 3 and array.shape[2] in (1, 3, 4):
                array = array
            elif array.ndim == 3:
                array = array[0]
            if array.ndim == 2:
                array = np.stack([array] * 3, axis=-1)
            elif array.ndim == 3 and array.shape[2] == 1:
                array = np.repeat(array, 3, axis=2)
            elif array.ndim == 3 and array.shape[2] > 4:
                array = array[..., :3]
            if array.dtype != np.uint8:
                array = np.clip(array, 0, 255).astype(np.uint8)
            return array
        except Exception:
            pass

    np_buffer = np.frombuffer(content, dtype=np.uint8)
    image_bgr = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise HTTPException(status_code=400, detail="Image illisible (format non supporté).")
    return image_bgr


@app.get("/")
async def racine():
    """Point de contrôle simple : confirme que l'API tourne."""
    return {"status": "ok", "docs": "/docs"}


@app.post("/api/segment")
async def api_segment(
    file: UploadFile = File(...), 
    patient_ref: str = Form("ANONYME"),
    client_name: str = Form(""),
    client_email: str = Form(""),
    client_phone: str = Form(""),
):
    """Reçoit une image IRM, lance la segmentation et retourne les résultats."""
    contenu = await file.read()
    if not contenu:
        raise HTTPException(status_code=400, detail="Aucun fichier IRM fourni.")

    image_bgr = load_image_from_upload_bytes(contenu, file.filename or "")

    resultats = run_segmentation(image_bgr)

    original_bytes, original_uri = _encode_png_data_uri(resultats["preprocessed_gray"])
    overlay_bytes, overlay_uri = _encode_png_data_uri(resultats["overlay"])
    heatmap_bytes, heatmap_uri = _encode_png_data_uri(resultats["uncertainty_heatmap"])

    session_id = uuid.uuid4().hex
    SESSIONS[session_id] = {
        "patient_ref": patient_ref,
        "client_name": client_name,
        "client_email": client_email,
        "client_phone": client_phone,
        "original_bytes": original_bytes,
        "overlay_bytes": overlay_bytes,
        "heatmap_bytes": heatmap_bytes,
        "metrics": resultats["metrics"],
        "pathology_scores": resultats["pathology_scores"],
    }

    return {
        "session_id": session_id,
        "original_image": original_uri,
        "overlay_image": overlay_uri,
        "uncertainty_heatmap": heatmap_uri,
        "metrics": resultats["metrics"],
        "pathology_scores": resultats["pathology_scores"],
        "disclaimer": DISCLAIMER,
    }


class RapportRequete(BaseModel):
    session_id: str


@app.post("/api/report")
async def api_report(requete: RapportRequete):
    """Génère et retourne le rapport PDF pour une session d'analyse existante."""
    session = SESSIONS.get(requete.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session d'analyse introuvable.")

    pdf_bytes = generate_pdf_report(
        patient_ref=session["patient_ref"],
        client_name=session.get("client_name", ""),
        client_email=session.get("client_email", ""),
        client_phone=session.get("client_phone", ""),
        original_png_bytes=session["original_bytes"],
        overlay_png_bytes=session["overlay_bytes"],
        heatmap_png_bytes=session["heatmap_bytes"],
        metrics=session["metrics"],
        pathology_scores=session["pathology_scores"],
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=rapport_lombalgie.pdf"},
    )
