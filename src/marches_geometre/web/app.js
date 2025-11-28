// src/marches_geometre/web/app.js

// Fichier JSON fixe généré par scripts/prepare_web_data.py
const JSON_FILE = "normalized_geometre_latest.json";

let allNotices = [];

// ---------- Tracking "déjà consulté" ----------

const VIEWED_KEY = "mg-viewed-notices";
let viewedIds = new Set();

function loadViewedIds() {
  try {
    const raw = localStorage.getItem(VIEWED_KEY);
    if (!raw) return;
    const arr = JSON.parse(raw);
    if (Array.isArray(arr)) {
      viewedIds = new Set(arr);
    }
  } catch (e) {
    console.warn("Impossible de lire les notices consultées :", e);
  }
}

function saveViewedIds() {
  try {
    localStorage.setItem(VIEWED_KEY, JSON.stringify([...viewedIds]));
  } catch (e) {
    console.warn("Impossible d’enregistrer les notices consultées :", e);
  }
}

// Id unique pour une notice (pour savoir si elle a déjà été vue)
function getNoticeId(notice) {
  if (notice.source_notice_id) return notice.source_notice_id;
  if (notice.url) return notice.url;
  // fallback si jamais rien d’autre n’existe
  return `${notice.source || "?"}-${notice.reference || ""}`;
}

// Helper utilisé par le filtre "État"
function isNoticeSeen(notice) {
  const id = getNoticeId(notice);
  if (!id) return false;
  return viewedIds.has(id);
}

// ---------- Utils dates & formats ----------

function parseIsoDate(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  return isNaN(d.getTime()) ? null : d;
}

function formatDateFr(dateStr) {
  if (!dateStr) return "";
  const d = parseIsoDate(dateStr);
  if (!d) return dateStr;
  return d.toLocaleDateString("fr-FR");
}

function isDeadlinePassed(deadlineDateStr, deadlineTimeStr) {
  if (!deadlineDateStr) return false;
  let dateTimeStr = deadlineDateStr;
  if (deadlineTimeStr) {
    const t = deadlineTimeStr.replace("h", ":");
    dateTimeStr += "T" + t;
  }
  const d = new Date(dateTimeStr);
  return !isNaN(d) && d < new Date();
}

// Avis publié il y a moins d'une semaine ?
function isNoticeRecent(publicationDateStr) {
  const d = parseIsoDate(publicationDateStr);
  if (!d) return false;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays <= 7;
}

// Date de publication la plus récente (pour fallback)
function computeMaxPublicationDate(notices) {
  const pubs = (notices || [])
    .map((n) => n.publication_date)
    .filter(Boolean)
    .sort()
    .reverse();
  return pubs[0] || null;
}

// ---------- Gestion du thème ----------

function updateThemeToggleUI(theme) {
  const btn = document.getElementById("themeToggle");
  if (!btn) return;

  const icon = btn.querySelector(".toggle-icon");
  const label = btn.querySelector(".toggle-label");

  const isDark = theme === "dark";
  btn.setAttribute("aria-pressed", String(isDark));

  if (isDark) {
    icon.textContent = "🌙";
    label.textContent = "Sombre";
  } else {
    icon.textContent = "☀️";
    label.textContent = "Clair";
  }
}

function applyTheme(theme) {
  const normalized = theme === "light" ? "light" : "dark";
  document.body.dataset.theme = normalized;
  localStorage.setItem("mg-theme", normalized);
  updateThemeToggleUI(normalized);
}

// ---------- Création d'une carte ----------

function createCard(notice) {
  const {
    source,
    reference,
    title,
    description,
    buyer_name,
    department,
    city,
    publication_date,
    deadline_date,
    deadline_time,
    url,
    estimated_budget,
    estimated_budget_raw,
  } = notice;

  const isNew = isNoticeRecent(publication_date);
  const noticeId = getNoticeId(notice);
  const hasBeenViewed = noticeId && viewedIds.has(noticeId);

  const link = document.createElement("a");
  link.className = "card-link";
  link.href = url || "#";
  link.target = "_blank";
  link.rel = "noopener noreferrer";

  const card = document.createElement("article");
  card.className = "card";

  // Badge "NOUVEAU"
  if (isNew) {
    const newBadge = document.createElement("span");
    newBadge.className = "badge badge-new";
    newBadge.textContent = "Nouveau";
    card.appendChild(newBadge);
  }

  // Header
  const headerRow = document.createElement("div");
  headerRow.className = "card-header-row";

  const titleEl = document.createElement("h2");
  titleEl.className = "card-title";
  titleEl.textContent = title || "(Sans titre)";

  const badges = document.createElement("div");
  badges.className = "badges";

  const bSource = document.createElement("span");
  bSource.className = "badge";
  bSource.textContent = (source || "").toUpperCase();
  if (source) bSource.classList.add(`badge-source-${source.toLowerCase()}`);
  badges.appendChild(bSource);

  if (reference) {
    const bRef = document.createElement("span");
    bRef.className = "badge badge-ref";
    bRef.textContent = reference;
    badges.appendChild(bRef);
  }

  headerRow.appendChild(titleEl);
  headerRow.appendChild(badges);

  // Meta
  const meta = document.createElement("div");
  meta.className = "card-meta";

  if (buyer_name) {
    const s = document.createElement("span");
    s.innerHTML = `<span class="card-meta-label">Acheteur</span> ${buyer_name}`;
    meta.appendChild(s);
  }

  if (department) {
    const s = document.createElement("span");
    s.innerHTML = `<span class="card-meta-label">Dépt.</span> ${department}`;
    meta.appendChild(s);
  }

  if (city) {
    const s = document.createElement("span");
    s.innerHTML = `<span class="card-meta-label">Ville</span> ${city}`;
    meta.appendChild(s);
  }

  // Footer
  const footer = document.createElement("div");
  footer.className = "card-footer";

  const left = document.createElement("div");
  left.className = "card-footer-left";

  if (publication_date) {
    const pub = document.createElement("div");
    pub.innerHTML = `<span class="card-meta-label">Publié le</span> ${formatDateFr(
      publication_date
    )}`;
    left.appendChild(pub);
  }

  if (estimated_budget != null || estimated_budget_raw) {
    const b = document.createElement("div");
    b.className = "card-budget";
    const val =
      estimated_budget != null
        ? new Intl.NumberFormat("fr-FR", {
            style: "currency",
            currency: "EUR",
            maximumFractionDigits: 0,
          }).format(estimated_budget)
        : estimated_budget_raw;
    b.textContent = `Budget estimé : ${val}`;
    left.appendChild(b);
  }

  const right = document.createElement("div");
  right.className = "card-footer-right";

  if (deadline_date) {
    const dl = document.createElement("div");
    dl.className = "card-deadline";
    if (isDeadlinePassed(deadline_date, deadline_time)) {
      dl.classList.add("card-deadline--passed");
    }
    dl.textContent = `Date limite : ${formatDateFr(deadline_date)}${
      deadline_time ? " à " + deadline_time : ""
    }`;
    right.appendChild(dl);
  }

  // Badge "Déjà consulté" si déjà cliqué avant
  if (hasBeenViewed) {
    const seenFlag = document.createElement("div");
    seenFlag.className = "card-seen-flag";
    seenFlag.textContent = "Déjà consulté";
    right.appendChild(seenFlag);
  }

  footer.appendChild(left);
  footer.appendChild(right);

  // Assemble
  card.appendChild(headerRow);
  card.appendChild(meta);
  card.appendChild(footer);

  link.appendChild(card);

  // Quand on clique sur la carte -> marquer comme consulté
  link.addEventListener("click", () => {
    if (!noticeId) return;

    viewedIds.add(noticeId);
    saveViewedIds();

    if (!card.querySelector(".card-seen-flag")) {
      const seenFlag = document.createElement("div");
      seenFlag.className = "card-seen-flag";
      seenFlag.textContent = "Déjà consulté";
      right.appendChild(seenFlag);
    }
  });

  return link;
}

// ---------- Filtres & rendu ----------

function applyFilters() {
  const dep = document.getElementById("departmentFilter").value;
  const src = document.getElementById("sourceFilter").value.toLowerCase();
  const search = document
    .getElementById("searchInput")
    .value.toLowerCase()
    .trim();
  const seen = document.getElementById("seenFilter").value;

  let filtered = allNotices.slice();

  if (dep) {
    filtered = filtered.filter((n) => (n.department || "") === dep);
  }

  if (src) {
    filtered = filtered.filter(
      (n) => (n.source || "").toLowerCase() === src
    );
  }

  if (search) {
    filtered = filtered.filter((n) => {
      const haystack =
        (n.title || "") +
        " " +
        (n.description || "") +
        " " +
        (n.buyer_name || "") +
        " " +
        (n.reference || "");
      return haystack.toLowerCase().includes(search);
    });
  }

  // Filtre consulté / non consulté
  if (seen === "seen") {
    filtered = filtered.filter((n) => isNoticeSeen(n));
  } else if (seen === "unseen") {
    filtered = filtered.filter((n) => !isNoticeSeen(n));
  }

  const emptyState = document.getElementById("emptyState");
  const container = document.getElementById("cardsContainer");
  container.innerHTML = "";

  if (!filtered.length) {
    emptyState.hidden = false;
    return;
  }
  emptyState.hidden = true;

  filtered.sort((a, b) => {
    const da = parseIsoDate(a.publication_date);
    const db = parseIsoDate(b.publication_date);
    if (!da && !db) return 0;
    if (!da) return 1;
    if (!db) return -1;
    return db - da;
  });

  filtered.forEach((n) => container.appendChild(createCard(n)));
}

// ---------- Init ----------

async function init() {
  // Charger l'historique "déjà consulté"
  loadViewedIds();

  // Thème initial
  const storedTheme = localStorage.getItem("mg-theme");
  applyTheme(storedTheme || "dark");

  try {
    const resp = await fetch(JSON_FILE);
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    const data = await resp.json();

    let generatedAt = null;

    if (Array.isArray(data)) {
      // Ancien format (juste un tableau)
      allNotices = data;
    } else {
      // Nouveau format : { generated_at, notices }
      generatedAt = data.generated_at || data.generatedAt || null;
      allNotices = data.notices || [];
    }

    const lastUpdateEl = document.getElementById("lastUpdate");

    if (generatedAt) {
      // On affiche la date du cron (date d'exécution pipeline)
      lastUpdateEl.textContent = formatDateFr(generatedAt);
    } else {
      // Fallback : date de publication max
      const maxPub = computeMaxPublicationDate(allNotices);
      lastUpdateEl.textContent = maxPub ? formatDateFr(maxPub) : "—";
    }

    applyFilters();
  } catch (e) {
    console.error("Erreur lors du chargement du JSON :", e);
    const container = document.getElementById("cardsContainer");
    container.innerHTML =
      "<p style='color:#f97373'>Erreur lors du chargement des données.</p>";
  }

  // Bouton de thème
  const themeBtn = document.getElementById("themeToggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const current =
        document.body.dataset.theme === "light" ? "light" : "dark";
      const next = current === "dark" ? "light" : "dark";
      applyTheme(next);
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  init();
  document
    .getElementById("departmentFilter")
    .addEventListener("change", applyFilters);
  document
    .getElementById("sourceFilter")
    .addEventListener("change", applyFilters);
  document
    .getElementById("seenFilter")
    .addEventListener("change", applyFilters);
  document
    .getElementById("searchInput")
    .addEventListener("input", applyFilters);
});
