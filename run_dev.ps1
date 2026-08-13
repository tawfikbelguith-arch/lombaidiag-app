# ============================================================
# Script de développement local - Lance le backend et le frontend
# ============================================================

Write-Host "🚀 Lancement du mode développement..." -ForegroundColor Cyan

# Vérifier les dépendances
Write-Host "`n📦 Vérification des dépendances..." -ForegroundColor Yellow

# Venv Python
$venvPath = ".\venv\Scripts\Activate.ps1"
if (-Not (Test-Path $venvPath)) {
    Write-Host "❌ Environnement virtuel non trouvé. Créez-le avec:" -ForegroundColor Red
    Write-Host "   python -m venv venv" -ForegroundColor Gray
    exit 1
}

Write-Host "`n✅ Activation de l'environnement virtuel..."
& $venvPath

# Ouvrir deux terminaux pour le backend et le frontend
Write-Host "`n📋 Lancez les commandes suivantes dans des terminaux séparés:" -ForegroundColor Cyan
Write-Host ""
Write-Host "Terminal 1 - Backend (FastAPI):" -ForegroundColor Green
Write-Host "  cd backend && uvicorn main:app --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "Terminal 2 - Frontend (Serveur HTTP simple):" -ForegroundColor Green
Write-Host "  cd frontend && python -m http.server 3000" -ForegroundColor Gray
Write-Host ""
Write-Host "Puis accédez à: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
