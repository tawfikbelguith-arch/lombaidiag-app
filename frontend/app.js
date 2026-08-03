// ============================================================
// app.js — logique frontend de la plateforme d'aide au diagnostic
// ============================================================

const API_BASE = window.LOMBAI_API_BASE || "http://localhost:8000";

const fileInput = document.getElementById("fileInput");
const fileLabel = document.getElementById("fileLabel");
const patientRefInput = document.getElementById("patientRef");
const analyzeBtn = document.getElementById("analyzeBtn");
const previewWrap = document.getElementById("previewWrap");
const previewImg = document.getElementById("previewImg");
const previewName = document.getElementById("previewName");
const loadingBox = document.getElementById("loading");
const errorBox = document.getElementById("errorBox");
const resultsSection = document.getElementById("resultsSection");
const downloadReportBtn = document.getElementById("downloadReportBtn");
const resetBtn = document.getElementById("resetBtn");

let selectedFile = null;
let currentSessionId = null;

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;

  selectedFile = file;
  analyzeBtn.disabled = false;
  fileLabel.textContent = "📁 " + file.name;

  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    previewName.textContent = `${file.name} — ${(file.size / 1024).toFixed(0)} Ko`;
    previewWrap.classList.remove("hidden");
  };
  reader.readAsDataURL(file);

  hideError();
});

analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  hideError();
  setLoading(true);
  resultsSection.classList.add("hidden");

  try {
    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("patient_ref", patientRefInput.value || "ANONYME");

    const response = await fetch(`${API_BASE}/api/segment`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Erreur serveur (${response.status})`);
    }

    const data = await response.json();
    currentSessionId = data.session_id;
    renderResults(data);
  } catch (err) {
    showError(
      "Échec de l'analyse : " +
        err.message +
        ". Vérifiez que le backend est lancé (voir README, uvicorn sur " +
        API_BASE +
        ")."
    );
  } finally {
    setLoading(false);
  }
});

downloadReportBtn.addEventListener("click", async () => {
  if (!currentSessionId) return;
  try {
    const response = await fetch(`${API_BASE}/api/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId }),
    });
    if (!response.ok) throw new Error("Impossible de générer le rapport.");

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "rapport_lombalgie.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    showError("Échec du téléchargement du rapport : " + err.message);
  }
});

resetBtn.addEventListener("click", () => {
  selectedFile = null;
  currentSessionId = null;
  fileInput.value = "";
  fileLabel.textContent = "📁 Choisir une image IRM";
  previewWrap.classList.add("hidden");
  resultsSection.classList.add("hidden");
  analyzeBtn.disabled = true;
  patientRefInput.value = "";
  hideError();
});

function setLoading(isLoading) {
  loadingBox.classList.toggle("hidden", !isLoading);
  analyzeBtn.disabled = isLoading || !selectedFile;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}
function hideError() {
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

function riskLevelClass(value) {
  if (value >= 0.66) return "high";
  if (value >= 0.33) return "medium";
  return "";
}

function renderResults(data) {
  document.getElementById("imgOriginal").src = data.original_image;
  document.getElementById("imgOverlay").src = data.overlay_image;
  document.getElementById("imgHeatmap").src = data.uncertainty_heatmap;

  // Tableau des métriques de segmentation
  const metricsLabels = {
    sc_area_ratio: "Surface canal spinal (ratio image)",
    vb_area_ratio: "Surface vertèbres (ratio image)",
    ivd_area_ratio: "Surface disques (ratio image)",
    mean_uncertainty: "Incertitude moyenne",
  };
  const metricsTable = document.getElementById("metricsTable");
  metricsTable.innerHTML = Object.entries(data.metrics)
    .map(
      ([key, value]) =>
        `<tr><td>${metricsLabels[key] || key}</td><td>${value}</td></tr>`
    )
    .join("");

  // Tableau + barres de risque pathologique
  const pathologyLabels = {
    disc_narrowing_risk: "Rétrécissement discal",
    spondylolisthesis_risk: "Spondylolisthésis",
    overall_confidence: "Confiance globale du modèle",
  };
  const pathologyTable = document.getElementById("pathologyTable");
  pathologyTable.innerHTML = Object.entries(data.pathology_scores)
    .map(
      ([key, value]) =>
        `<tr><td>${pathologyLabels[key] || key}</td><td>${value}</td></tr>`
    )
    .join("");

  const riskBars = document.getElementById("riskBars");
  riskBars.innerHTML = Object.entries(data.pathology_scores)
    .filter(([key]) => key !== "overall_confidence")
    .map(([key, value]) => {
      const pct = Math.round(value * 100);
      const cls = riskLevelClass(value);
      return `
        <div class="risk-row">
          <div class="risk-label"><span>${pathologyLabels[key] || key}</span><span>${pct}%</span></div>
          <div class="risk-track"><div class="risk-fill ${cls}" style="width:${pct}%"></div></div>
        </div>`;
    })
    .join("");

  document.getElementById("disclaimerText").textContent =
    "⚠ " + data.disclaimer;

  resultsSection.classList.remove("hidden");
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}
