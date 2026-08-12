// ============================================================
// app.js — logique frontend de la plateforme d'aide au diagnostic
// ============================================================

const API_BASE = window.LOMBAI_API_BASE || "http://localhost:8000";

let selectedFile = null;
let currentSessionId = null;

// Éléments DOM
let fileInput, fileLabel, patientRefInput, analyzeBtn, previewWrap, previewImg, previewName, loadingBox, errorBox, resultsSection, downloadReportBtn, resetBtn;
let clientNameInput, clientEmailInput, clientPhoneInput;

// Initialiser quand le DOM est prêt
document.addEventListener("DOMContentLoaded", () => {
  // Récupérer les références aux éléments DOM
  fileInput = document.getElementById("fileInput");
  fileLabel = document.getElementById("fileLabel");
  patientRefInput = document.getElementById("patientRef");
  clientNameInput = document.getElementById("clientName");
  clientEmailInput = document.getElementById("clientEmail");
  clientPhoneInput = document.getElementById("clientPhone");
  analyzeBtn = document.getElementById("analyzeBtn");
  previewWrap = document.getElementById("previewWrap");
  previewImg = document.getElementById("previewImg");
  previewName = document.getElementById("previewName");
  loadingBox = document.getElementById("loading");
  errorBox = document.getElementById("errorBox");
  resultsSection = document.getElementById("resultsSection");
  downloadReportBtn = document.getElementById("downloadReportBtn");
  resetBtn = document.getElementById("resetBtn");

  // Vérifier que tous les éléments critiques existent
  if (!fileInput || !analyzeBtn || !downloadReportBtn || !resetBtn) {
    console.error("Erreur : éléments HTML critiques manquants", {
      fileInput: !!fileInput,
      analyzeBtn: !!analyzeBtn,
      downloadReportBtn: !!downloadReportBtn,
      resetBtn: !!resetBtn,
    });
    return;
  }

  // Ajouter les event listeners
  fileInput.addEventListener("change", handleFileChange);
  analyzeBtn.addEventListener("click", handleAnalyze);
  downloadReportBtn.addEventListener("click", handleDownloadReport);
  resetBtn.addEventListener("click", handleReset);
});

function handleFileChange() {
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
}

async function handleAnalyze() {
  if (!selectedFile) return;

  hideError();
  setLoading(true);
  resultsSection.classList.add("hidden");

  try {
    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("patient_ref", patientRefInput ? patientRefInput.value || "ANONYME" : "ANONYME");
    formData.append("client_name", clientNameInput ? clientNameInput.value || "" : "");
    formData.append("client_email", clientEmailInput ? clientEmailInput.value || "" : "");
    formData.append("client_phone", clientPhoneInput ? clientPhoneInput.value || "" : "");

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
}

async function handleDownloadReport() {
  if (!currentSessionId) {
    showError("Aucune session active. Veuillez d'abord lancer une analyse.");
    return;
  }

  const nom = clientNameInput && clientNameInput.value ? clientNameInput.value : "Anonyme";
  const email = clientEmailInput && clientEmailInput.value ? clientEmailInput.value : "";
  const whatsapp = clientPhoneInput && clientPhoneInput.value ? clientPhoneInput.value : "";

  try {
    const response = await fetch(`${API_BASE}/api/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        nom_patient: nom,
        email: email,
        whatsapp: whatsapp,
      }),
    });

    if (!response.ok) {
      throw new Error("Impossible de générer le rapport.");
    }

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
}

function handleReset() {
  selectedFile = null;
  currentSessionId = null;
  if (fileInput) fileInput.value = "";
  if (fileLabel) fileLabel.textContent = "📁 Choisir une image IRM";
  if (previewWrap) previewWrap.classList.add("hidden");
  if (resultsSection) resultsSection.classList.add("hidden");
  if (analyzeBtn) analyzeBtn.disabled = true;
  if (patientRefInput) patientRefInput.value = "";
  if (clientNameInput) clientNameInput.value = "";
  if (clientEmailInput) clientEmailInput.value = "";
  if (clientPhoneInput) clientPhoneInput.value = "";
  hideError();
}

function setLoading(isLoading) {
  if (!loadingBox || !analyzeBtn) return;
  loadingBox.classList.toggle("hidden", !isLoading);
  analyzeBtn.disabled = isLoading || !selectedFile;
}

function showError(message) {
  if (!errorBox) return;
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function hideError() {
  if (!errorBox) return;
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

function riskLevelClass(value) {
  if (value >= 0.66) return "high";
  if (value >= 0.33) return "medium";
  return "";
}

function renderResults(data) {
  // Vérifier que tous les éléments existent
  const imgOriginal = document.getElementById("imgOriginal");
  const imgOverlay = document.getElementById("imgOverlay");
  const imgHeatmap = document.getElementById("imgHeatmap");
  const metricsTable = document.getElementById("metricsTable");
  const pathologyTable = document.getElementById("pathologyTable");
  const riskBars = document.getElementById("riskBars");
  const disclaimerText = document.getElementById("disclaimerText");

  if (!imgOriginal || !metricsTable) {
    showError("Erreur : éléments de résultats manquants dans le HTML");
    return;
  }

  if (imgOriginal) imgOriginal.src = data.original_image;
  if (imgOverlay) imgOverlay.src = data.overlay_image;
  if (imgHeatmap) imgHeatmap.src = data.uncertainty_heatmap;

  // Tableau des métriques de segmentation
  const metricsLabels = {
    sc_area_ratio: "Surface canal spinal (ratio image)",
    vb_area_ratio: "Surface vertèbres (ratio image)",
    ivd_area_ratio: "Surface disques (ratio image)",
    mean_uncertainty: "Incertitude moyenne",
  };

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

  if (pathologyTable) {
    pathologyTable.innerHTML = Object.entries(data.pathology_scores)
      .map(
        ([key, value]) =>
          `<tr><td>${pathologyLabels[key] || key}</td><td>${value}</td></tr>`
      )
      .join("");
  }

  if (riskBars) {
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
  }

  if (disclaimerText) {
    disclaimerText.textContent = "⚠ " + data.disclaimer;
  }

  if (resultsSection) {
    resultsSection.classList.remove("hidden");
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

