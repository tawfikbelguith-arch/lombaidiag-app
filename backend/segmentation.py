"""
segmentation.py
================
Pipeline de segmentation de la colonne lombaire.

IMPORTANT — LIRE AVANT UTILISATION CLINIQUE :
Ce module contient un pipeline de DÉMONSTRATION basé sur du traitement d'image
classique (seuillage adaptatif, morphologie mathématique, détection de contours).
Il simule la sortie attendue d'un vrai modèle de segmentation par diffusion
(type SpineSegDiff) pour permettre de construire et tester toute
l'application (upload, visualisation, rapport, etc.) sans dépendre
de poids de modèle entraînés.

CE PIPELINE N'A AUCUNE VALEUR DIAGNOSTIQUE. Il ne doit jamais être utilisé
pour un vrai patient.

Pour brancher le vrai modèle :
1. Remplacer le contenu de la fonction `run_segmentation()` par :
   - le chargement du checkpoint PyTorch entraîné (SpineSegDiff),
   - le prétraitement identique à celui utilisé à l'entraînement
     (normalisation percentile 98, recalage RAS+, resize 320x320),
   - l'inférence par diffusion (few-step, cf. papier SpineSegDiff),
   - l'ensemble d'incertitude (cf. formules dans le rapport d'analyse).
2. Conserver la même signature de fonction et le même format de sortie
   (dictionnaire avec masques, carte d'incertitude, scores) pour que le
   reste de l'application (API + frontend) continue de fonctionner
   sans modification.
"""

import numpy as np
import cv2
from typing import Dict, Tuple


TARGET_SIZE = 320  # même résolution que dans l'article (320x320)

# Couleurs BGR (OpenCV) pour l'overlay, cohérentes avec les figures de l'article
COLOR_SC = (255, 100, 0)    # bleu   -> canal spinal
COLOR_VB = (0, 200, 0)      # vert   -> vertèbres
COLOR_IVD = (0, 0, 255)     # rouge  -> disques intervertébraux


def preprocess(image_gray: np.ndarray) -> np.ndarray:
    """Normalisation par percentile 98 + resize, comme dans le pipeline SPIDER."""
    p98 = np.percentile(image_gray, 98)
    p98 = max(p98, 1e-6)
    normalized = np.clip((image_gray / p98) * 255.0, 0, 255).astype(np.uint8)
    resized = cv2.resize(normalized, (TARGET_SIZE, TARGET_SIZE), interpolation=cv2.INTER_LINEAR)
    return resized


def _segment_vertebrae(img: np.ndarray) -> np.ndarray:
    """Détecte les régions vertébrales (zones claires, compactes) — heuristique de démo."""
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(img)
    min_area = (TARGET_SIZE * TARGET_SIZE) * 0.005
    for c in contours:
        if cv2.contourArea(c) > min_area:
            cv2.drawContours(mask, [c], -1, 255, thickness=cv2.FILLED)
    return mask


def _segment_discs(img: np.ndarray, vb_mask: np.ndarray) -> np.ndarray:
    """Approxime les disques comme les fines bandes situées entre deux vertèbres."""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    dilated_vb = cv2.dilate(vb_mask, kernel, iterations=1)
    band = cv2.subtract(dilated_vb, vb_mask)

    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    _, dark_regions = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    disc_mask = cv2.bitwise_and(band, dark_regions)
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    disc_mask = cv2.morphologyEx(disc_mask, cv2.MORPH_CLOSE, kernel_small)
    return disc_mask


def _segment_canal(img: np.ndarray, vb_mask: np.ndarray) -> np.ndarray:
    """Approxime le canal spinal comme une région sombre postérieure aux vertèbres."""
    h, w = img.shape
    posterior_region = np.zeros_like(img)
    posterior_region[:, : int(w * 0.55)] = 255  # hypothèse : canal du côté gauche de l'image

    blurred = cv2.GaussianBlur(img, (7, 7), 0)
    _, dark_regions = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY_INV)

    candidate = cv2.bitwise_and(posterior_region, dark_regions)
    candidate = cv2.bitwise_and(candidate, cv2.bitwise_not(vb_mask))

    contours, _ = cv2.findContours(candidate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(img)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) > (TARGET_SIZE * TARGET_SIZE) * 0.01:
            cv2.drawContours(mask, [largest], -1, 255, thickness=cv2.FILLED)
    return mask


def _compute_uncertainty_map(img: np.ndarray, sc: np.ndarray, vb: np.ndarray, ivd: np.ndarray) -> np.ndarray:
    """
    Simule une carte d'incertitude en s'appuyant sur le gradient d'intensité
    près des bords des masques (les vrais modèles de diffusion l'obtiennent
    par l'entropie d'un ensemble d'échantillons stochastiques, cf. Eq. 1-2
    du papier SpineSegDiff).
    """
    combined = cv2.bitwise_or(cv2.bitwise_or(sc, vb), ivd)
    edges = cv2.Canny(combined, 50, 150)
    dilated_edges = cv2.dilate(edges, np.ones((9, 9), np.uint8))
    uncertainty = cv2.GaussianBlur(dilated_edges, (15, 15), 0).astype(np.float32) / 255.0
    return uncertainty


def _estimate_pathology_risk(vb_mask: np.ndarray, ivd_mask: np.ndarray) -> Dict[str, float]:
    """
    Heuristique de démonstration : estime un score de risque de rétrécissement
    discal / spondylolisthésis à partir de l'irrégularité de l'espacement
    vertical entre vertèbres détectées.
    Un vrai système reprendrait ici un classifieur multi-label entraîné
    (cf. Partie 3 du rapport d'analyse : classification pathologique sur ROI).
    """
    contours, _ = cv2.findContours(vb_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centers_y = sorted(
        [cv2.boundingRect(c)[1] + cv2.boundingRect(c)[3] / 2 for c in contours if cv2.contourArea(c) > 200]
    )

    if len(centers_y) < 3:
        return {
            "disc_narrowing_risk": 0.0,
            "spondylolisthesis_risk": 0.0,
            "overall_confidence": 0.3,
        }

    gaps = np.diff(centers_y)
    mean_gap = np.mean(gaps)
    std_gap = np.std(gaps)
    irregularity = float(std_gap / (mean_gap + 1e-6))

    disc_narrowing_risk = float(np.clip(irregularity * 1.5, 0, 1))
    spondylolisthesis_risk = float(np.clip(irregularity * 1.2, 0, 1))
    overall_confidence = float(np.clip(1.0 - irregularity, 0.2, 0.95))

    return {
        "disc_narrowing_risk": round(disc_narrowing_risk, 3),
        "spondylolisthesis_risk": round(spondylolisthesis_risk, 3),
        "overall_confidence": round(overall_confidence, 3),
    }


def build_overlay(img_gray: np.ndarray, sc: np.ndarray, vb: np.ndarray, ivd: np.ndarray) -> np.ndarray:
    """Construit une image couleur avec les masques superposés (SC bleu, VB vert, IVD rouge)."""
    base = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
    overlay = base.copy()
    overlay[sc > 0] = COLOR_SC
    overlay[vb > 0] = COLOR_VB
    overlay[ivd > 0] = COLOR_IVD
    blended = cv2.addWeighted(overlay, 0.45, base, 0.55, 0)
    return blended


def build_uncertainty_heatmap(uncertainty: np.ndarray) -> np.ndarray:
    """Convertit la carte d'incertitude en heatmap couleur affichable."""
    heat = (uncertainty * 255).astype(np.uint8)
    heatmap = cv2.applyColorMap(heat, cv2.COLORMAP_JET)
    return heatmap


def run_segmentation(image_bgr: np.ndarray) -> Dict:
    """
    Point d'entrée principal du pipeline. Reçoit une image (BGR, OpenCV) et
    retourne un dictionnaire structuré exploitable par l'API et le frontend.

    C'est CETTE FONCTION qu'il faut remplacer par l'appel au vrai modèle
    SpineSegDiff entraîné (voir docstring du module).
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    img = preprocess(gray)

    vb_mask = _segment_vertebrae(img)
    ivd_mask = _segment_discs(img, vb_mask)
    sc_mask = _segment_canal(img, vb_mask)

    uncertainty = _compute_uncertainty_map(img, sc_mask, vb_mask, ivd_mask)
    pathology_scores = _estimate_pathology_risk(vb_mask, ivd_mask)

    overlay = build_overlay(img, sc_mask, vb_mask, ivd_mask)
    heatmap = build_uncertainty_heatmap(uncertainty)

    def pixel_ratio(mask: np.ndarray) -> float:
        return round(float(np.count_nonzero(mask)) / mask.size, 4)

    metrics = {
        "sc_area_ratio": pixel_ratio(sc_mask),
        "vb_area_ratio": pixel_ratio(vb_mask),
        "ivd_area_ratio": pixel_ratio(ivd_mask),
        "mean_uncertainty": round(float(np.mean(uncertainty)), 4),
    }

    return {
        "preprocessed_gray": img,
        "sc_mask": sc_mask,
        "vb_mask": vb_mask,
        "ivd_mask": ivd_mask,
        "overlay": overlay,
        "uncertainty_heatmap": heatmap,
        "metrics": metrics,
        "pathology_scores": pathology_scores,
    }
