"""
report.py
=========
Génère un rapport PDF récapitulatif d'un examen : image originale, overlay de
segmentation, carte d'incertitude, métriques et scores de risque pathologique.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from sheets import save_analysis


def generate_pdf_report(
    patient_ref: str,
    client_name: str,
    client_email: str,
    client_phone: str,
    original_png_bytes: bytes,
    overlay_png_bytes: bytes,
    heatmap_png_bytes: bytes,
    metrics: dict,
    pathology_scores: dict,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleCustom", parent=styles["Title"], fontSize=18, spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "SubtitleCustom", parent=styles["Normal"], fontSize=10, textColor=colors.grey
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer", parent=styles["Normal"], fontSize=8, textColor=colors.red, spaceBefore=10
    )
    h2_style = ParagraphStyle("H2Custom", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)

    elements = []
    elements.append(Paragraph("Rapport d'analyse IRM — Lombalgie", title_style))
    elements.append(
        Paragraph(
            f"Référence patient : {patient_ref} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Images", h2_style))
    img_w = 150
    imgs_row = Table(
        [
            [
                RLImage(io.BytesIO(original_png_bytes), width=img_w, height=img_w),
                RLImage(io.BytesIO(overlay_png_bytes), width=img_w, height=img_w),
                RLImage(io.BytesIO(heatmap_png_bytes), width=img_w, height=img_w),
            ],
            ["IRM originale (prétraitée)", "Segmentation (SC/VB/IVD)", "Carte d'incertitude"],
        ]
    )
    imgs_row.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 1), (-1, 1), 8),
                ("TEXTCOLOR", (0, 1), (-1, 1), colors.grey),
            ]
        )
    )
    elements.append(imgs_row)

    elements.append(Paragraph("Métriques de segmentation", h2_style))
    metrics_data = [["Indicateur", "Valeur"]] + [
        [k.replace("_", " ").capitalize(), str(v)] for k, v in metrics.items()
    ]
    metrics_table = Table(metrics_data, colWidths=[280, 150])
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(metrics_table)

    elements.append(Paragraph("Scores de risque pathologique (estimation)", h2_style))
    path_data = [["Pathologie / Indicateur", "Score (0-1)"]] + [
        [k.replace("_", " ").capitalize(), str(v)] for k, v in pathology_scores.items()
    ]
    path_table = Table(path_data, colWidths=[280, 150])
    path_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3D9D9")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(path_table)

    elements.append(
        Paragraph(
            "⚠ AVERTISSEMENT : ce rapport est généré par un pipeline de démonstration "
            "(traitement d'image classique) et n'a AUCUNE valeur diagnostique. "
            "Il ne doit en aucun cas remplacer l'avis d'un professionnel de santé. "
            "Ce prototype est destiné uniquement à illustrer l'architecture logicielle "
            "d'une future application clinique, qui devra intégrer un modèle validé "
            "(ex. SpineSegDiff) et obtenir les certifications réglementaires requises "
            "(marquage CE / FDA) avant tout usage réel.",
            disclaimer_style,
        )
    )

    # Enregistrer l'analyse dans Google Sheets
    save_analysis(
        nom_patient=client_name or patient_ref,
        rapport=f"Analyse IRM lombaire - {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        email=client_email or None,
        whatsapp=client_phone or None,
    )

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
