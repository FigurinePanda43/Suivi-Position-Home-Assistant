/**
 * Suivi de Présence — carte Lovelace
 * Version 1.0.2
 *
 * Chargée automatiquement par l'intégration (aucune ressource à déclarer).
 * Sans dépendance : JavaScript natif, API websocket de l'intégration,
 * téléchargements par chemins signés Home Assistant (compatibles navigateur
 * et applications compagnon).
 *
 * Configuration (toutes les clés sont optionnelles) :
 *   type: custom:suivi-presence-card
 *   title: Suivi de Présence          # false pour masquer l'en-tête
 *   default_period: today             # today | 24h | 7d | 30d | all
 *   persons: [person.jean]            # limiter l'affichage à ces personnes
 *   show_summary: true                # temps par zone sur la période
 *   show_history: true                # liste des changements de zone
 *   show_export: true                 # boutons CSV / Excel (juste sous les filtres)
 *   show_details: true                # bloc « Détails techniques » replié
 *   history_limit: 50                 # lignes affichées avant « Afficher plus »
 *   stale_after_minutes: 120          # position GPS considérée ancienne au-delà
 */

const CARD_VERSION = "1.0.2";
const CARD_TAG = "suivi-presence-card";

const WS_OVERVIEW = "suivi_presence/overview";
const WS_HISTORY = "suivi_presence/history";
const URL_CSV_FULL = "/api/suivi_presence/download";
const URL_CSV = "/api/suivi_presence/download/csv";
const URL_EXCEL = "/api/suivi_presence/download/excel";

const PERIODS = ["today", "24h", "7d", "30d", "all", "custom"];

const STRINGS = {
  fr: {
    title: "Suivi de Présence",
    tracking_on: "Suivi actif",
    tracking_off: "Suivi inactif",
    persons_count: (n) => `${n} personne${n > 1 ? "s" : ""}`,
    no_persons:
      "Aucune personne suivie. Créez des entités « person » avec un traqueur d'appareil, puis vérifiez les options de l'intégration.",
    not_loaded: "L'intégration Suivi de Présence n'est pas chargée.",
    loading: "Chargement…",
    home: "Maison",
    away: "Absent",
    unknown: "Inconnu",
    unavailable: "Indisponible",
    since: (d) => `depuis ${d}`,
    since_unknown: "durée inconnue",
    gps_updated: (rel) => `Position mise à jour ${rel}`,
    gps_accuracy: (m) => `±${m} m`,
    gps_none: "Pas de position GPS",
    gps_stale: "Position ancienne",
    alerts_title: "À vérifier",
    alert_unavailable: (name) => `${name} : traqueur indisponible, dernière zone connue affichée.`,
    alert_stale: (name, rel) => `${name} : position GPS non mise à jour ${rel}.`,
    alert_load_error: (msg) => `Fichier CSV : ${msg}`,
    alert_excel: "Export Excel indisponible sur ce serveur.",
    period: "Période",
    p_today: "Aujourd'hui",
    p_24h: "24 h",
    p_7d: "7 jours",
    p_30d: "30 jours",
    p_all: "Tout",
    p_custom: "Personnalisé",
    from: "Du",
    to: "au",
    filter_persons: "Personnes",
    all_persons: "Toutes",
    summary_title: "Temps par zone",
    summary_empty: "Aucune donnée sur la période.",
    ongoing: "en cours",
    visits: (n) => `${n} passage${n > 1 ? "s" : ""}`,
    history_title: "Changements de zone",
    history_empty: "Aucun changement de zone sur la période.",
    history_empty_today: (since) => `Aucun changement de zone depuis minuit (${since}).`,
    last_change: (when, person, from, to) => `Dernier changement enregistré : ${when} — ${person}, ${from} → ${to}.`,
    no_records_yet: "Aucun changement enregistré pour l'instant : le premier sera ajouté au prochain changement de zone.",
    records_total: (n) => `${n} enregistrement${n > 1 ? "s" : ""} au total dans l'historique`,
    widen_7d: "Voir les 7 derniers jours",
    history_count: (shown, total) =>
      shown < total ? `${shown} sur ${total} changements` : `${total} changement${total > 1 ? "s" : ""}`,
    show_more: "Afficher plus",
    after: (d, zone) => `après ${d} à ${zone}`,
    export_title: "Exporter la période",
    export_csv: "CSV",
    export_excel: "Excel",
    export_started: "Téléchargement démarré",
    export_failed: (m) => `Échec du téléchargement : ${m}`,
    export_excel_disabled: "Export Excel indisponible sur ce serveur",
    details: "Détails techniques",
    d_csv: "Fichier CSV",
    d_records: "Enregistrements",
    d_range: "Données disponibles",
    d_version: "Version",
    d_services: "Services",
    today_label: "Aujourd'hui",
    yesterday_label: "Hier",
    now: "à l'instant",
    error_generic: "Erreur",
  },
  en: {
    title: "Presence Tracker",
    tracking_on: "Tracking active",
    tracking_off: "Tracking inactive",
    persons_count: (n) => `${n} person${n > 1 ? "s" : ""}`,
    no_persons:
      "No tracked person. Create “person” entities with a device tracker, then check the integration options.",
    not_loaded: "The Presence Tracker integration is not loaded.",
    loading: "Loading…",
    home: "Home",
    away: "Away",
    unknown: "Unknown",
    unavailable: "Unavailable",
    since: (d) => `for ${d}`,
    since_unknown: "unknown duration",
    gps_updated: (rel) => `Position updated ${rel}`,
    gps_accuracy: (m) => `±${m} m`,
    gps_none: "No GPS position",
    gps_stale: "Stale position",
    alerts_title: "Needs attention",
    alert_unavailable: (name) => `${name}: tracker unavailable, last known zone shown.`,
    alert_stale: (name, rel) => `${name}: GPS position not updated ${rel}.`,
    alert_load_error: (msg) => `CSV file: ${msg}`,
    alert_excel: "Excel export unavailable on this server.",
    period: "Period",
    p_today: "Today",
    p_24h: "24 h",
    p_7d: "7 days",
    p_30d: "30 days",
    p_all: "All",
    p_custom: "Custom",
    from: "From",
    to: "to",
    filter_persons: "Persons",
    all_persons: "All",
    summary_title: "Time per zone",
    summary_empty: "No data for this period.",
    ongoing: "ongoing",
    visits: (n) => `${n} visit${n > 1 ? "s" : ""}`,
    history_title: "Zone changes",
    history_empty: "No zone change in this period.",
    history_empty_today: (since) => `No zone change since midnight (${since}).`,
    last_change: (when, person, from, to) => `Last recorded change: ${when} — ${person}, ${from} → ${to}.`,
    no_records_yet: "Nothing recorded yet: the first entry will be added on the next zone change.",
    records_total: (n) => `${n} record${n > 1 ? "s" : ""} in the whole history`,
    widen_7d: "Show the last 7 days",
    history_count: (shown, total) =>
      shown < total ? `${shown} of ${total} changes` : `${total} change${total > 1 ? "s" : ""}`,
    show_more: "Show more",
    after: (d, zone) => `after ${d} at ${zone}`,
    export_title: "Export this period",
    export_csv: "CSV",
    export_excel: "Excel",
    export_started: "Download started",
    export_failed: (m) => `Download failed: ${m}`,
    export_excel_disabled: "Excel export unavailable on this server",
    details: "Technical details",
    d_csv: "CSV file",
    d_records: "Records",
    d_range: "Available data",
    d_version: "Version",
    d_services: "Services",
    today_label: "Today",
    yesterday_label: "Yesterday",
    now: "just now",
    error_generic: "Error",
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const pad2 = (n) => String(n).padStart(2, "0");

const localDateString = (date) => `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;

const toIsoWithOffset = (date) => {
  const offset = -date.getTimezoneOffset();
  const sign = offset >= 0 ? "+" : "-";
  const abs = Math.abs(offset);
  return (
    `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}` +
    `T${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(date.getSeconds())}` +
    `${sign}${pad2(Math.floor(abs / 60))}:${pad2(abs % 60)}`
  );
};

function formatDuration(seconds, lang) {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds) || seconds < 0) return "—";
  const total = Math.round(seconds);
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const d = lang === "fr" ? "j" : "d";
  if (days > 0) return `${days} ${d} ${hours} h`;
  if (hours > 0) return `${hours} h ${pad2(minutes)}`;
  if (minutes > 0) return `${minutes} min`;
  return `${total} s`;
}

function formatRelative(date, lang, strings) {
  if (!date || Number.isNaN(date.getTime())) return "";
  const diff = (date.getTime() - Date.now()) / 1000;
  const abs = Math.abs(diff);
  if (abs < 45) return strings.now;
  let value;
  let unit;
  if (abs < 3600) {
    value = Math.round(diff / 60);
    unit = "minute";
  } else if (abs < 86400) {
    value = Math.round(diff / 3600);
    unit = "hour";
  } else {
    value = Math.round(diff / 86400);
    unit = "day";
  }
  try {
    return new Intl.RelativeTimeFormat(lang, { numeric: "auto" }).format(value, unit);
  } catch (err) {
    return `${Math.abs(value)} ${unit}`;
  }
}

function formatTime(date, lang) {
  try {
    return new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit" }).format(date);
  } catch (err) {
    return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
  }
}

function formatDateLong(date, lang) {
  try {
    return new Intl.DateTimeFormat(lang, { weekday: "long", day: "numeric", month: "long" }).format(date);
  } catch (err) {
    return localDateString(date);
  }
}

function formatDateShort(date, lang) {
  try {
    return new Intl.DateTimeFormat(lang, { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
  } catch (err) {
    return localDateString(date);
  }
}

function zoneClass(zone) {
  if (zone === "home") return "home";
  if (zone === "not_home") return "away";
  if (zone === "unknown" || zone === "unavailable" || !zone) return "unknown";
  return "zone";
}

function initials(name) {
  return String(name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------

class SuiviPresenceCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._overview = null;
    this._history = null;
    this._period = "today";
    this._customStart = "";
    this._customEnd = "";
    this._selectedPersons = new Set();
    this._limit = 50;
    this._loadingHistory = false;
    this._error = null;
    this._signature = "";
    this._refreshTimer = null;
    this._clockTimer = null;
    this._historyRequest = 0;
  }

  // --- Lovelace API ---------------------------------------------------------

  static getStubConfig() {
    return {
      title: "Suivi de Présence",
      default_period: "today",
      show_summary: true,
      show_history: true,
      show_export: true,
      history_limit: 30,
    };
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  setConfig(config) {
    const period = config.default_period || "today";
    if (!PERIODS.includes(period) || period === "custom") {
      if (period !== "custom") {
        throw new Error(`default_period doit valoir today, 24h, 7d, 30d ou all (reçu : ${period})`);
      }
    }
    if (config.persons && !Array.isArray(config.persons)) {
      throw new Error("persons doit être une liste d'entités person.*");
    }
    this._config = {
      title: config.title === undefined ? null : config.title,
      default_period: period,
      persons: config.persons || null,
      show_summary: config.show_summary !== false,
      show_history: config.show_history !== false,
      show_export: config.show_export !== false,
      show_details: config.show_details !== false,
      history_limit: Number(config.history_limit) > 0 ? Number(config.history_limit) : 50,
      stale_after_minutes: Number(config.stale_after_minutes) > 0 ? Number(config.stale_after_minutes) : 120,
    };
    this._period = this._config.default_period;
    this._limit = this._config.history_limit;
    this._restorePeriod();
    if (this._rendered) {
      this._renderAll();
      this._loadHistory();
    }
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (!this._rendered) {
      this._renderShell();
      this._rendered = true;
    }
    if (first) {
      this._loadOverview().then(() => this._loadHistory());
      return;
    }
    // Only react to changes of the entities we care about.
    const signature = this._computeSignature();
    if (signature !== this._signature) {
      this._signature = signature;
      this._scheduleRefresh();
    }
  }

  connectedCallback() {
    if (!this._clockTimer) {
      this._clockTimer = setInterval(() => {
        if (this._overview) this._renderPersons();
      }, 60000);
    }
  }

  disconnectedCallback() {
    if (this._clockTimer) {
      clearInterval(this._clockTimer);
      this._clockTimer = null;
    }
    if (this._refreshTimer) {
      clearTimeout(this._refreshTimer);
      this._refreshTimer = null;
    }
  }

  // --- Data -------------------------------------------------------------------

  get _lang() {
    const language = (this._hass && (this._hass.locale?.language || this._hass.language)) || "fr";
    return language.toLowerCase().startsWith("fr") ? "fr" : "en";
  }

  get _t() {
    return STRINGS[this._lang];
  }

  _computeSignature() {
    if (!this._hass) return "";
    const parts = [];
    const persons = this._overview?.persons || [];
    for (const person of persons) {
      const state = this._hass.states[person.entity_id];
      if (state) parts.push(`${person.entity_id}:${state.state}:${state.last_updated}`);
    }
    const sensors = Object.values(this._hass.entities || {}).filter(
      (entry) => entry.platform === "suivi_presence"
    );
    for (const entry of sensors) {
      const state = this._hass.states[entry.entity_id];
      if (state) parts.push(`${entry.entity_id}:${state.state}`);
    }
    return parts.join("|");
  }

  _scheduleRefresh() {
    if (this._refreshTimer) clearTimeout(this._refreshTimer);
    this._refreshTimer = setTimeout(async () => {
      this._refreshTimer = null;
      const before = this._overview?.total_records;
      await this._loadOverview();
      if (this._overview && this._overview.total_records !== before) {
        this._loadHistory();
      }
    }, 400);
  }

  async _loadOverview() {
    if (!this._hass) return;
    try {
      const data = await this._hass.callWS({ type: WS_OVERVIEW });
      if (this._config.persons) {
        const allowed = new Set(this._config.persons);
        data.persons = (data.persons || []).filter((p) => allowed.has(p.entity_id));
      }
      this._overview = data;
      this._error = null;
    } catch (err) {
      this._overview = null;
      this._error = err && err.code === "not_loaded" ? this._t.not_loaded : `${this._t.error_generic} : ${err.message || err}`;
    }
    this._signature = this._computeSignature();
    this._renderAll();
  }

  get _storageKey() {
    // Includes the configured default so that changing the card config resets the memory.
    return `suivi-presence-card:${this._config.title || ""}:${this._config.default_period}`;
  }

  _restorePeriod() {
    try {
      const raw = window.localStorage.getItem(this._storageKey);
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (PERIODS.includes(saved.period)) this._period = saved.period;
      if (typeof saved.customStart === "string") this._customStart = saved.customStart;
      if (typeof saved.customEnd === "string") this._customEnd = saved.customEnd;
    } catch (err) {
      // Private mode, storage disabled: keep the configured default.
    }
  }

  _savePeriod() {
    try {
      window.localStorage.setItem(
        this._storageKey,
        JSON.stringify({ period: this._period, customStart: this._customStart, customEnd: this._customEnd })
      );
    } catch (err) {
      // Ignore: remembering the period is a convenience only.
    }
  }

  _periodBounds() {
    const now = new Date();
    switch (this._period) {
      case "today":
        return { start: localDateString(now), end: null };
      case "24h":
        return { start: toIsoWithOffset(new Date(now.getTime() - 24 * 3600 * 1000)), end: null };
      case "7d":
        return { start: toIsoWithOffset(new Date(now.getTime() - 7 * 86400 * 1000)), end: null };
      case "30d":
        return { start: toIsoWithOffset(new Date(now.getTime() - 30 * 86400 * 1000)), end: null };
      case "custom":
        return { start: this._customStart || null, end: this._customEnd || null };
      default:
        return { start: null, end: null };
    }
  }

  _activePersons() {
    // Names/entity ids sent to the backend; empty = all visible persons.
    if (this._selectedPersons.size > 0) return [...this._selectedPersons];
    if (this._config.persons) return [...this._config.persons];
    return null;
  }

  async _loadHistory() {
    if (!this._hass || !this._overview) return;
    if (!this._config.show_history && !this._config.show_summary && !this._config.show_export) return;
    const request = ++this._historyRequest;
    this._loadingHistory = true;
    this._renderHistory();
    const { start, end } = this._periodBounds();
    const msg = { type: WS_HISTORY, limit: Math.min(Math.max(this._limit, 1), 2000) };
    if (start) msg.start = start;
    if (end) msg.end = end;
    const persons = this._activePersons();
    if (persons) msg.persons = persons;
    try {
      const data = await this._hass.callWS(msg);
      if (request !== this._historyRequest) return;
      this._history = data;
      this._error = null;
    } catch (err) {
      if (request !== this._historyRequest) return;
      this._history = null;
      this._error = `${this._t.error_generic} : ${err.message || err}`;
    }
    this._loadingHistory = false;
    this._renderSummary();
    this._renderHistory();
    this._renderExport();
  }

  // --- Rendering ------------------------------------------------------------------

  _renderShell() {
    this.shadowRoot.innerHTML = `
      <style>${SuiviPresenceCard.styles}</style>
      <ha-card>
        <div class="card-content">
          <div id="header"></div>
          <div id="alerts"></div>
          <div id="persons"></div>
          <div id="period"></div>
          <div id="export"></div>
          <div id="summary"></div>
          <div id="history"></div>
          <div id="details"></div>
        </div>
      </ha-card>
    `;
    const root = this.shadowRoot;
    root.addEventListener("click", (event) => this._onClick(event));
    root.addEventListener("change", (event) => this._onChange(event));
  }

  _renderAll() {
    this._renderHeader();
    this._renderAlerts();
    this._renderPersons();
    this._renderPeriod();
    this._renderSummary();
    this._renderHistory();
    this._renderExport();
    this._renderDetails();
  }

  _section(id) {
    return this.shadowRoot.getElementById(id);
  }

  _renderHeader() {
    const t = this._t;
    const el = this._section("header");
    if (this._config.title === false) {
      el.innerHTML = "";
      return;
    }
    const title = this._config.title || t.title;
    let status = "";
    if (this._overview) {
      const on = this._overview.tracking;
      const n = (this._overview.persons || []).length;
      status = `<span class="status ${on ? "on" : "off"}"><span class="dot"></span>${esc(on ? t.tracking_on : t.tracking_off)} · ${esc(t.persons_count(n))}</span>`;
    } else if (this._error) {
      status = `<span class="status off"><span class="dot"></span>${esc(t.tracking_off)}</span>`;
    }
    el.innerHTML = `
      <div class="header">
        <h1 class="title">${esc(title)}</h1>
        ${status}
      </div>`;
  }

  _staleThresholdMs() {
    return this._config.stale_after_minutes * 60000;
  }

  _personIssues(person) {
    const t = this._t;
    const issues = [];
    if (!person.available) issues.push({ type: "unavailable", text: t.alert_unavailable(person.name) });
    if (person.latitude !== null && person.latitude !== undefined && person.last_updated) {
      const updated = new Date(person.last_updated);
      if (Date.now() - updated.getTime() > this._staleThresholdMs()) {
        issues.push({ type: "stale", text: t.alert_stale(person.name, formatRelative(updated, this._lang, t)) });
      }
    }
    return issues;
  }

  _renderAlerts() {
    const t = this._t;
    const el = this._section("alerts");
    const alerts = [];
    if (this._error) alerts.push(this._error);
    if (this._overview) {
      if (this._overview.load_error) alerts.push(t.alert_load_error(this._overview.load_error));
      for (const person of this._overview.persons || []) {
        for (const issue of this._personIssues(person)) alerts.push(issue.text);
      }
    }
    if (alerts.length === 0) {
      el.innerHTML = "";
      return;
    }
    el.innerHTML = `
      <div class="alerts">
        <div class="alerts-title"><ha-icon icon="mdi:alert-circle-outline"></ha-icon>${esc(t.alerts_title)}</div>
        <ul>${alerts.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>
      </div>`;
  }

  _zoneLabel(zone) {
    const t = this._t;
    if (zone === "home") return t.home;
    if (zone === "not_home") return t.away;
    if (zone === "unknown" || !zone) return t.unknown;
    if (zone === "unavailable") return t.unavailable;
    return zone;
  }

  _renderPersons() {
    const t = this._t;
    const el = this._section("persons");
    if (!this._overview) {
      el.innerHTML = this._error ? "" : `<div class="empty">${esc(t.loading)}</div>`;
      return;
    }
    const persons = this._overview.persons || [];
    if (persons.length === 0) {
      el.innerHTML = `<div class="empty">${esc(t.no_persons)}</div>`;
      return;
    }
    const lang = this._lang;
    el.innerHTML = `<div class="persons">${persons
      .map((person) => {
        const state = this._hass.states[person.entity_id];
        const picture = state?.attributes?.entity_picture || person.picture;
        const since = person.since ? new Date(person.since) : null;
        const sinceText = since ? t.since(formatDuration((Date.now() - since.getTime()) / 1000, lang)) : t.since_unknown;
        const issues = this._personIssues(person);
        const zone = person.available ? person.zone : person.zone;
        const cls = person.available ? zoneClass(zone) : "unknown";
        let gps = t.gps_none;
        let gpsClass = "muted";
        if (person.latitude !== null && person.latitude !== undefined && person.last_updated) {
          const updated = new Date(person.last_updated);
          const stale = issues.some((i) => i.type === "stale");
          const accuracy = person.gps_accuracy ? ` · ${t.gps_accuracy(Math.round(person.gps_accuracy))}` : "";
          gps = `${stale ? t.gps_stale + " · " : ""}${t.gps_updated(formatRelative(updated, lang, t))}${accuracy}`;
          gpsClass = stale ? "warn" : "muted";
        }
        const avatar = picture
          ? `<img class="avatar" src="${esc(picture)}" alt="" loading="lazy">`
          : `<div class="avatar initials">${esc(initials(person.name))}</div>`;
        return `
          <button class="person ${issues.length ? "has-issue" : ""}" data-action="more-info" data-entity="${esc(person.entity_id)}" title="${esc(person.entity_id)}">
            ${avatar}
            <div class="person-main">
              <div class="person-row">
                <span class="name">${esc(person.name)}</span>
                <span class="zone-badge ${cls}">${esc(person.available ? this._zoneLabel(zone) : t.unavailable)}</span>
              </div>
              <div class="person-row sub">
                <span>${esc(sinceText)}</span>
                <span class="${gpsClass}">${esc(gps)}</span>
              </div>
            </div>
            <ha-icon class="chevron" icon="mdi:chevron-right"></ha-icon>
          </button>`;
      })
      .join("")}</div>`;
  }

  _renderPeriod() {
    const t = this._t;
    const el = this._section("period");
    if (!this._overview || (!this._config.show_history && !this._config.show_summary && !this._config.show_export)) {
      el.innerHTML = "";
      return;
    }
    const chips = ["today", "24h", "7d", "30d", "all", "custom"]
      .map(
        (p) =>
          `<button class="chip ${this._period === p ? "active" : ""}" data-action="period" data-period="${p}">${esc(t[`p_${p}`])}</button>`
      )
      .join("");
    const custom =
      this._period === "custom"
        ? `<div class="custom-range">
             <label>${esc(t.from)} <input type="date" id="custom-start" value="${esc(this._customStart)}"></label>
             <label>${esc(t.to)} <input type="date" id="custom-end" value="${esc(this._customEnd)}"></label>
           </div>`
        : "";
    const persons = this._overview.persons || [];
    let personChips = "";
    if (persons.length > 1) {
      personChips = `<div class="chips persons-filter">
          <button class="chip small ${this._selectedPersons.size === 0 ? "active" : ""}" data-action="person-all">${esc(t.all_persons)}</button>
          ${persons
            .map(
              (p) =>
                `<button class="chip small ${this._selectedPersons.has(p.entity_id) ? "active" : ""}" data-action="person-toggle" data-entity="${esc(p.entity_id)}">${esc(p.name)}</button>`
            )
            .join("")}
        </div>`;
    }
    el.innerHTML = `
      <div class="period">
        <div class="chips">${chips}</div>
        ${custom}
        ${personChips}
      </div>`;
  }

  _periodLabel() {
    const t = this._t;
    const lang = this._lang;
    if (this._period === "custom") {
      const s = this._customStart ? formatDateShort(new Date(`${this._customStart}T00:00:00`), lang) : "…";
      const e = this._customEnd ? formatDateShort(new Date(`${this._customEnd}T00:00:00`), lang) : "…";
      return `${t.from} ${s} ${t.to} ${e}`;
    }
    return t[`p_${this._period}`];
  }

  _renderSummary() {
    const t = this._t;
    const el = this._section("summary");
    if (!this._config.show_summary || !this._overview) {
      el.innerHTML = "";
      return;
    }
    const summary = this._history?.summary || {};
    const names = Object.keys(summary).sort((a, b) => a.localeCompare(b));
    let body;
    if (!this._history && this._loadingHistory) {
      body = `<div class="empty small">${esc(t.loading)}</div>`;
    } else if (names.length === 0) {
      body = `<div class="empty small">${esc(t.summary_empty)}</div>`;
    } else {
      const lang = this._lang;
      body = names
        .map((name) => {
          const zones = Object.entries(summary[name])
            .filter(([, s]) => s.seconds > 0)
            .sort((a, b) => b[1].seconds - a[1].seconds);
          const total = zones.reduce((acc, [, s]) => acc + s.seconds, 0) || 1;
          const bar = zones
            .map(([zone, s]) => {
              const pct = Math.max((s.seconds / total) * 100, 1.5);
              return `<span class="seg ${zoneClass(zone)}" style="width:${pct.toFixed(2)}%" title="${esc(this._zoneLabel(zone))} · ${esc(formatDuration(s.seconds, lang))}"></span>`;
            })
            .join("");
          const legend = zones
            .map(
              ([zone, s]) =>
                `<span class="legend-item"><span class="swatch ${zoneClass(zone)}"></span>${esc(this._zoneLabel(zone))} <strong>${esc(formatDuration(s.seconds, lang))}</strong>${s.ongoing ? ` <em>(${esc(t.ongoing)})</em>` : ""} <span class="muted">· ${esc(t.visits(s.visits))}</span></span>`
            )
            .join("");
          return `
            <div class="summary-person">
              <div class="summary-name">${esc(name)}</div>
              <div class="bar">${bar}</div>
              <div class="legend">${legend}</div>
            </div>`;
        })
        .join("");
    }
    el.innerHTML = `
      <div class="section">
        <div class="section-title">${esc(t.summary_title)} <span class="muted">· ${esc(this._periodLabel())}</span></div>
        ${body}
      </div>`;
  }

  _renderHistory() {
    const t = this._t;
    const el = this._section("history");
    if (!this._config.show_history || !this._overview) {
      el.innerHTML = "";
      return;
    }
    const lang = this._lang;
    let body;
    if (!this._history && this._loadingHistory) {
      body = `<div class="empty small">${esc(t.loading)}</div>`;
    } else if (!this._history || this._history.records.length === 0) {
      body = this._renderEmptyHistory();
    } else {
      const records = this._history.records;
      const groups = new Map();
      for (const record of records) {
        const date = new Date(record.timestamp_utc || record.timestamp);
        const key = localDateString(date);
        if (!groups.has(key)) groups.set(key, { date, items: [] });
        groups.get(key).items.push({ record, date });
      }
      const today = localDateString(new Date());
      const yesterday = localDateString(new Date(Date.now() - 86400000));
      const showPerson = (this._overview.persons || []).length > 1;
      body = [...groups.values()]
        .map((group) => {
          const key = localDateString(group.date);
          const label = key === today ? t.today_label : key === yesterday ? t.yesterday_label : formatDateLong(group.date, lang);
          const rows = group.items
            .map(({ record, date }) => {
              const dur =
                record.duration_seconds !== null && record.duration_seconds !== undefined
                  ? `<span class="muted">${esc(t.after(formatDuration(record.duration_seconds, lang), this._zoneLabel(record.previous_zone)))}</span>`
                  : "";
              return `
                <div class="hist-row">
                  <span class="time">${esc(formatTime(date, lang))}</span>
                  ${showPerson ? `<span class="hist-person">${esc(record.person)}</span>` : ""}
                  <span class="zone-badge ${zoneClass(record.previous_zone)}">${esc(this._zoneLabel(record.previous_zone))}</span>
                  <ha-icon class="arrow" icon="mdi:arrow-right-thin"></ha-icon>
                  <span class="zone-badge ${zoneClass(record.new_zone)}">${esc(this._zoneLabel(record.new_zone))}</span>
                  ${dur}
                </div>`;
            })
            .join("");
          return `<div class="hist-day"><div class="hist-date">${esc(label)}</div>${rows}</div>`;
        })
        .join("");
      const total = this._history.total;
      const shown = records.length;
      const more =
        shown < total
          ? `<button class="chip small" data-action="more">${esc(t.show_more)}</button>`
          : "";
      body += `<div class="hist-footer"><span class="muted">${esc(t.history_count(shown, total))}</span>${more}</div>`;
    }
    el.innerHTML = `
      <div class="section">
        <div class="section-title">${esc(t.history_title)} <span class="muted">· ${esc(this._periodLabel())}</span></div>
        ${body}
      </div>`;
  }

  _renderEmptyHistory() {
    // An empty period must never look like lost data: say why it is empty,
    // recall the last recorded change and offer to widen the period.
    const t = this._t;
    const lang = this._lang;
    const total = this._overview.total_records || 0;
    const last = this._overview.last_record;
    let reason;
    if (this._period === "today") {
      const midnight = new Date();
      midnight.setHours(0, 0, 0, 0);
      reason = t.history_empty_today(formatRelative(midnight, lang, t));
    } else {
      reason = t.history_empty;
    }
    let context;
    if (total === 0 || !last) {
      context = t.no_records_yet;
    } else {
      const when = new Date(last.timestamp);
      const whenText = Number.isNaN(when.getTime())
        ? String(last.timestamp)
        : `${formatDateShort(when, lang)} ${formatTime(when, lang)}`;
      context = `${t.last_change(whenText, last.person, this._zoneLabel(last.previous_zone), this._zoneLabel(last.new_zone))} ${t.records_total(total)}.`;
    }
    const widen =
      (this._period === "today" || this._period === "24h") && total > 0
        ? `<button class="chip small" data-action="period" data-period="7d">${esc(t.widen_7d)}</button>`
        : "";
    return `
      <div class="empty small">${esc(reason)}</div>
      <div class="hist-footer"><span class="muted">${esc(context)}</span>${widen}</div>`;
  }

  _renderExport() {
    const t = this._t;
    const el = this._section("export");
    if (!this._config.show_export || !this._overview) {
      el.innerHTML = "";
      return;
    }
    const excelOk = !!this._overview.excel_available;
    const count = this._history ? this._history.total : null;
    const countText = count === null ? "" : `<span class="muted">${esc(t.history_count(count, count))}</span>`;
    el.innerHTML = `
      <div class="export">
        <div class="export-label">${esc(t.export_title)} <span class="muted">· ${esc(this._periodLabel())}</span></div>
        <div class="export-buttons">
          ${countText}
          <button class="btn" data-action="download" data-kind="csv"><ha-icon icon="mdi:file-delimited-outline"></ha-icon>${esc(t.export_csv)}</button>
          <button class="btn excel" data-action="download" data-kind="excel" ${excelOk ? "" : `disabled title="${esc(t.export_excel_disabled)}"`}><ha-icon icon="mdi:microsoft-excel"></ha-icon>${esc(t.export_excel)}</button>
        </div>
        ${excelOk ? "" : `<div class="muted small-text">${esc(t.alert_excel)}</div>`}
      </div>`;
  }

  _renderDetails() {
    const t = this._t;
    const el = this._section("details");
    if (!this._config.show_details || !this._overview) {
      el.innerHTML = "";
      return;
    }
    const lang = this._lang;
    const range = this._overview.data_range || {};
    let rangeText = "—";
    if (range.start_date && range.end_date) {
      rangeText = `${formatDateShort(new Date(range.start_date), lang)} → ${formatDateShort(new Date(range.end_date), lang)}`;
    }
    el.innerHTML = `
      <details class="details">
        <summary>${esc(t.details)}</summary>
        <dl>
          <dt>${esc(t.d_csv)}</dt><dd><code class="path">${esc(this._overview.csv_path)}</code></dd>
          <dt>${esc(t.d_records)}</dt><dd>${esc(this._overview.total_records)}</dd>
          <dt>${esc(t.d_range)}</dt><dd>${esc(rangeText)}</dd>
          <dt>${esc(t.d_version)}</dt><dd>${esc(this._overview.version || "?")} (carte ${esc(CARD_VERSION)})</dd>
          <dt>${esc(t.d_services)}</dt><dd><code>suivi_presence.export_csv</code> · <code>suivi_presence.export_excel</code> · <code>suivi_presence.clear_history</code></dd>
        </dl>
      </details>`;
  }

  // --- Interactions ------------------------------------------------------------------

  _onClick(event) {
    const target = event.composedPath().find((node) => node.dataset && node.dataset.action);
    if (!target) return;
    const action = target.dataset.action;
    if (action === "more-info") {
      this._fire("hass-more-info", { entityId: target.dataset.entity });
    } else if (action === "period") {
      this._period = target.dataset.period;
      this._limit = this._config.history_limit;
      if (this._period === "custom" && !this._customStart) {
        const now = new Date();
        this._customEnd = localDateString(now);
        this._customStart = localDateString(new Date(now.getTime() - 6 * 86400000));
      }
      this._savePeriod();
      this._renderPeriod();
      this._loadHistory();
    } else if (action === "person-all") {
      this._selectedPersons.clear();
      this._renderPeriod();
      this._loadHistory();
    } else if (action === "person-toggle") {
      const id = target.dataset.entity;
      if (this._selectedPersons.has(id)) this._selectedPersons.delete(id);
      else this._selectedPersons.add(id);
      this._renderPeriod();
      this._loadHistory();
    } else if (action === "more") {
      this._limit = Math.min(this._limit + this._config.history_limit, 2000);
      this._loadHistory();
    } else if (action === "download") {
      this._download(target.dataset.kind);
    }
  }

  _onChange(event) {
    const target = event.composedPath()[0];
    if (!target || !target.id) return;
    if (target.id === "custom-start") this._customStart = target.value;
    if (target.id === "custom-end") this._customEnd = target.value;
    if (target.id === "custom-start" || target.id === "custom-end") {
      if (this._customStart && this._customEnd && this._customEnd < this._customStart) {
        [this._customStart, this._customEnd] = [this._customEnd, this._customStart];
        this._renderPeriod();
      }
      this._savePeriod();
      this._loadHistory();
    }
  }

  _fire(type, detail) {
    this.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true }));
  }

  _toast(message) {
    this._fire("hass-notification", { message });
  }

  _downloadQuery() {
    const params = new URLSearchParams();
    const { start, end } = this._periodBounds();
    if (start) params.set("start_date", start);
    if (end) params.set("end_date", end);
    const persons = this._activePersons();
    if (persons && persons.length) params.set("persons", persons.join(","));
    return params.toString();
  }

  async _download(kind) {
    const t = this._t;
    if (kind === "excel" && !this._overview?.excel_available) {
      this._toast(t.alert_excel);
      return;
    }
    const query = this._downloadQuery();
    let path;
    if (kind === "excel") path = query ? `${URL_EXCEL}?${query}` : URL_EXCEL;
    else path = query ? `${URL_CSV}?${query}` : URL_CSV_FULL;
    try {
      // Signed paths are how Home Assistant itself downloads files: the URL
      // carries a short-lived signature, so no bearer token and no blob: URL
      // are needed, and the companion apps handle the download natively.
      const signed = await this._hass.callWS({ type: "auth/sign_path", path, expires: 120 });
      const url = typeof this._hass.hassUrl === "function" ? this._hass.hassUrl(signed.path) : signed.path;
      const link = document.createElement("a");
      link.href = url;
      link.download = "";
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      link.remove();
      this._toast(t.export_started);
    } catch (err) {
      this._toast(t.export_failed(err?.message || err));
    }
  }

  // --- Styles ------------------------------------------------------------------------

  static get styles() {
    return `
      :host { display: block; }
      ha-card { overflow: hidden; }
      .card-content { padding: 16px; display: flex; flex-direction: column; gap: 14px; }
      .header { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
      .title { margin: 0; font-size: 1.25rem; font-weight: 500; color: var(--primary-text-color); line-height: 1.3; }
      .status { display: inline-flex; align-items: center; gap: 6px; font-size: 0.85rem; color: var(--secondary-text-color); white-space: nowrap; }
      .status .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--error-color, #db4437); }
      .status.on .dot { background: var(--success-color, #43a047); }

      .alerts { background: color-mix(in srgb, var(--warning-color, #ffa600) 14%, transparent); border-left: 4px solid var(--warning-color, #ffa600); border-radius: 8px; padding: 10px 12px; }
      .alerts-title { display: flex; align-items: center; gap: 6px; font-weight: 500; margin-bottom: 4px; }
      .alerts ul { margin: 0; padding-left: 18px; font-size: 0.9rem; }
      .alerts li { margin: 2px 0; }

      .persons { display: flex; flex-direction: column; gap: 6px; }
      .person { display: flex; align-items: center; gap: 12px; width: 100%; text-align: left; background: var(--secondary-background-color, rgba(0,0,0,0.04)); border: none; border-radius: 12px; padding: 10px 12px; cursor: pointer; color: inherit; font: inherit; }
      .person:hover { background: color-mix(in srgb, var(--primary-color) 10%, var(--secondary-background-color, transparent)); }
      .person:focus-visible { outline: 2px solid var(--primary-color); }
      .person.has-issue { box-shadow: inset 0 0 0 1px var(--warning-color, #ffa600); }
      .avatar { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; flex: none; }
      .avatar.initials { display: flex; align-items: center; justify-content: center; background: var(--primary-color); color: var(--text-primary-color, #fff); font-weight: 600; font-size: 0.95rem; }
      .person-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
      .person-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
      .person-row.sub { font-size: 0.8rem; color: var(--secondary-text-color); }
      .name { font-weight: 500; font-size: 1rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .chevron { color: var(--secondary-text-color); flex: none; --mdc-icon-size: 20px; }
      .muted { color: var(--secondary-text-color); font-weight: 400; }
      .warn { color: var(--warning-color, #ffa600); font-weight: 500; }
      .small-text { font-size: 0.8rem; }

      .zone-badge { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 0.8rem; font-weight: 500; line-height: 1.5; white-space: nowrap; }
      .zone-badge.home, .swatch.home, .seg.home { background: var(--success-color, #43a047); color: #fff; }
      .zone-badge.away, .swatch.away, .seg.away { background: var(--warning-color, #ffa600); color: #fff; }
      .zone-badge.zone, .swatch.zone, .seg.zone { background: var(--info-color, var(--primary-color, #1e88e5)); color: #fff; }
      .zone-badge.unknown, .swatch.unknown, .seg.unknown { background: var(--disabled-color, #9e9e9e); color: #fff; }

      .period { display: flex; flex-direction: column; gap: 8px; }
      .chips { display: flex; flex-wrap: wrap; gap: 6px; }
      .chip { border: 1px solid var(--divider-color, rgba(0,0,0,0.12)); background: transparent; color: var(--primary-text-color); border-radius: 999px; padding: 6px 12px; font: inherit; font-size: 0.85rem; cursor: pointer; line-height: 1.2; }
      .chip.small { padding: 4px 10px; font-size: 0.8rem; }
      .chip:hover { background: var(--secondary-background-color, rgba(0,0,0,0.04)); }
      .chip.active { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color, #fff); }
      .custom-range { display: flex; gap: 12px; flex-wrap: wrap; font-size: 0.85rem; color: var(--secondary-text-color); }
      .custom-range label { display: flex; align-items: center; gap: 6px; }
      .custom-range input { font: inherit; padding: 4px 6px; border: 1px solid var(--divider-color, rgba(0,0,0,0.12)); border-radius: 6px; background: var(--card-background-color, #fff); color: var(--primary-text-color); }

      .section { display: flex; flex-direction: column; gap: 8px; }
      .section-title { font-weight: 500; font-size: 0.95rem; }
      .empty { color: var(--secondary-text-color); font-style: italic; padding: 8px 0; }
      .empty.small { font-size: 0.85rem; padding: 4px 0; }

      .summary-person { display: flex; flex-direction: column; gap: 4px; }
      .summary-name { font-size: 0.85rem; font-weight: 500; }
      .bar { display: flex; height: 10px; border-radius: 5px; overflow: hidden; background: var(--divider-color, rgba(0,0,0,0.08)); }
      .seg { display: block; height: 100%; }
      .legend { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 0.8rem; }
      .legend-item { display: inline-flex; align-items: center; gap: 5px; }
      .swatch { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }

      .hist-day { display: flex; flex-direction: column; gap: 2px; }
      .hist-date { font-size: 0.8rem; color: var(--secondary-text-color); text-transform: capitalize; margin: 6px 0 2px; }
      .hist-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 5px 0; border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.08)); font-size: 0.88rem; }
      .hist-row:last-child { border-bottom: none; }
      .time { font-variant-numeric: tabular-nums; color: var(--secondary-text-color); min-width: 44px; }
      .hist-person { font-weight: 500; min-width: 70px; }
      .arrow { color: var(--secondary-text-color); --mdc-icon-size: 18px; }
      .hist-footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 0.8rem; padding-top: 4px; }

      .export { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px 12px; padding-bottom: 12px; border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.08)); }
      .export-label { font-weight: 500; font-size: 0.95rem; }
      .export-buttons { display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex-wrap: wrap; font-size: 0.8rem; margin-left: auto; }
      .export .small-text { flex-basis: 100%; }
      .btn { display: inline-flex; align-items: center; gap: 6px; border: none; border-radius: 8px; padding: 8px 14px; font: inherit; font-size: 0.85rem; font-weight: 500; cursor: pointer; background: var(--primary-color); color: var(--text-primary-color, #fff); }
      .btn.excel { background: #217346; color: #fff; }
      .btn:disabled { opacity: 0.45; cursor: not-allowed; }
      .btn ha-icon { --mdc-icon-size: 18px; }

      .details { font-size: 0.8rem; color: var(--secondary-text-color); }
      .details summary { cursor: pointer; }
      .details dl { display: grid; grid-template-columns: max-content 1fr; gap: 4px 12px; margin: 8px 0 0; }
      .details dt { font-weight: 500; }
      .details dd { margin: 0; overflow-wrap: anywhere; }
      .details dd code { white-space: nowrap; }
      .details dd code.path { white-space: normal; word-break: break-all; }
      code { font-size: 0.78rem; background: var(--secondary-background-color, rgba(0,0,0,0.04)); padding: 1px 4px; border-radius: 4px; }

      @media (max-width: 480px) {
        .card-content { padding: 12px; }
        .person-row { flex-direction: column; align-items: flex-start; gap: 2px; }
        .person-row.sub { flex-direction: column; }
        .hist-person { min-width: 0; }
        .export-label { flex-basis: 100%; }
        .export-buttons { justify-content: stretch; width: 100%; }
        .export-buttons .btn { flex: 1; justify-content: center; }
      }
    `;
  }
}

if (!customElements.get(CARD_TAG)) {
  customElements.define(CARD_TAG, SuiviPresenceCard);
  window.customCards = window.customCards || [];
  if (!window.customCards.some((card) => card.type === CARD_TAG)) {
    window.customCards.push({
      type: CARD_TAG,
      name: "Suivi de Présence",
      description: "Qui est où, depuis quand, historique des zones et exports CSV / Excel.",
      preview: false,
      documentationURL: "https://github.com/FigurinePanda43/Suivi-Position-Home-Assistant",
    });
  }
  console.info(
    `%c SUIVI-PRESENCE-CARD %c ${CARD_VERSION} `,
    "color: white; background: #305496; font-weight: bold;",
    "color: #305496; background: white; font-weight: bold;"
  );
}
