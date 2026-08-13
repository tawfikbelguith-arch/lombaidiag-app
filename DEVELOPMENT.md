# Guide de Développement Local

## Configuration pour le développement

Le frontend et le backend détectent automatiquement s'ils sont en mode développement (localhost) ou production.

### Frontend (http://localhost:3000)
- Détecte automatiquement que vous êtes sur `localhost`
- Pointe vers le backend local : `http://localhost:8000`
- Toutes les requêtes API vont au backend local

### Backend (http://localhost:8000)
- Accepte les requêtes CORS de `localhost` sur les ports :
  - `http://localhost:3000` (port par défaut)
  - `http://localhost:5173` (port Vite)
  - `http://127.0.0.1:3000` et `127.0.0.1:5173`
- Accepte aussi les requêtes de `https://lombaidiag.netlify.app` (production)

---

## Lancement en développement

### Option 1 : Deux terminaux séparés (recommandé)

**Terminal 1 - Backend FastAPI :**
```bash
cd backend
uvicorn main:app --reload
```
Backend disponible à : `http://localhost:8000`

**Terminal 2 - Frontend :**
```bash
cd frontend
python -m http.server 3000
```
Frontend disponible à : `http://localhost:3000`

---

### Option 2 : Avec PowerShell (Windows)
```powershell
.\run_dev.ps1
```
Puis suivez les instructions affichées.

---

## Architecture

```
Frontend (localhost:3000)
    ↓
    └─→ Détecte localhost ✓
        └─→ Utilise API_BASE = http://localhost:8000
            ↓
    Backend (localhost:8000)
        ↓
        └─→ CORS accepte localhost:3000 ✓
            └─→ Retourne les résultats
```

---

## Production

- **Frontend** : Déployé sur Netlify (`https://lombaidiag.netlify.app`)
- **Backend** : Déployé sur Render (`https://lombaidiag-app.onrender.com`)
- Les deux communiquent automatiquement via leurs URLs de production
- CORS configuré pour accepter uniquement `https://lombaidiag.netlify.app`

---

## Configuration manuelle

Si vous avez besoin de pointer vers un autre backend :

### Option A : Console navigateur
```javascript
// Dans la console du navigateur
window.LOMBAI_API_BASE = "http://votre-backend:8000";
location.reload();
```

### Option B : Variable d'environnement
Modifier `frontend/index.html` ligne ~560 :
```javascript
const API_BASE = "http://votre-url-backend";
```

---

## Dépannage

### ❌ "Cannot connect to backend"
1. Vérifiez que le backend s'exécute : `http://localhost:8000/docs`
2. Vérifiez que vous êtes sur `localhost` (pas `127.0.0.1` seul)
3. Vérifiez les ports : backend = 8000, frontend = 3000

### ❌ Erreur CORS
Le backend doit avoir `localhost:3000` dans `allow_origins`
(Déjà configuré dans `backend/main.py`)

### ❌ Fichier index.html non trouvé
Lancez le frontend depuis le dossier `frontend/` :
```bash
cd frontend
python -m http.server 3000
```
