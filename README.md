# LombAIDiag — Plateforme d'aide au diagnostic de la lombalgie (prototype)

Prototype fonctionnel d'une application web pour l'analyse d'IRM lombaires :
upload d'image → segmentation (canal spinal / vertèbres / disques) → carte
d'incertitude → estimation de risque pathologique → rapport PDF.

> ⚠️ **AVERTISSEMENT IMPORTANT**
> Ce projet est un **prototype pédagogique**. Le module de segmentation
> (`backend/segmentation.py`) utilise un pipeline de **traitement d'image
> classique** (seuillage, morphologie mathématique) à la place d'un vrai
> modèle de deep learning entraîné (type SpineSegDiff). **Il n'a aucune
> valeur diagnostique** et ne doit jamais être utilisé sur de vraies données
> patients pour une décision médicale. Il sert uniquement à démontrer
> l'architecture logicielle complète (frontend + API + rapport) dans
> laquelle un vrai modèle pourra être branché.

## Structure du projet

```
lombalgie-app/
├── backend/
│   ├── main.py            # API FastAPI (endpoints /api/segment, /api/report)
│   ├── segmentation.py    # Pipeline de segmentation (À REMPLACER par le vrai modèle)
│   ├── report.py          # Génération du rapport PDF (reportlab)
│   └── requirements.txt
├── frontend/
│   ├── index.html         # Interface utilisateur
│   ├── style.css           # Style (thème "visualiseur radiologique")
│   └── app.js              # Logique d'appel à l'API
└── README.md
```

## Installation et lancement

### 1. Backend (API FastAPI)

```bash
python -m venv venv

# PowerShell (Windows)
.\venv\Scripts\Activate.ps1

# Git Bash / WSL / macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

L'API est alors disponible sur `http://localhost:8000`.
Documentation interactive auto-générée : `http://localhost:8000/docs`.

### 2. Frontend

Aucune compilation nécessaire (HTML/CSS/JS natif). Servez simplement le
dossier `frontend/` avec un petit serveur HTTP :

```bash
cd frontend
python -m http.server 8080
```

Puis ouvrez `http://localhost:8080` dans votre navigateur.

Si votre backend ne tourne pas sur `http://localhost:8000`, changez l'URL
dans `git --version` (variable `API_BASE`), ou définissez-la depuis la
console du navigateur avant chargement :
```html
<script>window.LOMBAI_API_BASE = "http://mon-serveur:8000";</script>
```

## Utilisation

1. Ouvrez l'application dans le navigateur.
2. Renseignez une référence patient (optionnel).
3. Importez une image IRM lombaire (PNG/JPG — coupe sagittale).
4. Cliquez sur « Lancer l'analyse ».
5. Consultez la segmentation, la carte d'incertitude et les scores de risque.
6. Téléchargez le rapport PDF si besoin.

## Brancher le vrai modèle SpineSegDiff (prochaine étape)

Toute la logique de segmentation est isolée dans `backend/segmentation.py`,
dans la fonction `run_segmentation(image_bgr)`. Pour intégrer un vrai modèle
entraîné :

1. Charger le checkpoint PyTorch du modèle entraîné au démarrage de l'API
   (dans `main.py`, une seule fois, pas à chaque requête).
2. Reproduire le prétraitement exact utilisé à l'entraînement (normalisation
   percentile 98, recalage RAS+, resize 320×320 — cf. papier SpineSegDiff).
3. Remplacer le corps de `run_segmentation()` par l'inférence par diffusion
   (few-step, avec la stratégie de pré-segmentation nnU-Net) et le calcul de
   la carte d'incertitude par l'ensemble stochastique (cf. les formules du
   papier : moyenne des probabilités, entropie, fusion pondérée temporelle).
4. Conserver strictement le même format de sortie (dictionnaire avec les
   mêmes clés) pour que l'API et le frontend continuent de fonctionner sans
   aucune modification supplémentaire.
5. Remplacer l'heuristique `_estimate_pathology_risk()` par un vrai
   classifieur multi-label entraîné sur les régions d'intérêt (ROI) issues
   de la segmentation anatomique.

## Prochaines étapes suggérées pour une version production

- Authentification des utilisateurs (radiologues, administrateurs).
- Vraie base de données (PostgreSQL) + stockage objet (S3/MinIO) au lieu du
  dictionnaire `SESSIONS` en mémoire.
- Support natif du format DICOM (via `pydicom`) en plus de PNG/JPG.
- Journalisation et traçabilité (audit) de chaque analyse.
- Validation clinique et démarche de certification réglementaire (marquage
  CE / FDA) avant tout déploiement réel.
