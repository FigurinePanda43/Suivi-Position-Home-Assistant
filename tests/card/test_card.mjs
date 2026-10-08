/**
 * Headless test of the Lovelace card with jsdom.
 *
 * Run from the repository root:  node tests/card/test_card.mjs
 * Requires `jsdom` (npm install jsdom) resolvable from the current directory or
 * from NODE_PATH.
 *
 * It renders the card with a fake `hass` object whose `callWS` answers like the
 * integration's websocket API, then checks the DOM and the interactions
 * (period chips, person filter, "show more", CSV / Excel downloads via
 * auth/sign_path).
 */
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";

const require = createRequire(import.meta.url);
const { JSDOM } = require("jsdom");

const cardPath = path.resolve("custom_components/suivi_presence/www/suivi-presence-card.js");
const source = readFileSync(cardPath, "utf8");

const dom = new JSDOM(`<!DOCTYPE html><body></body>`, { runScripts: "outside-only", pretendToBeVisual: true, url: "http://localhost/" });
const { window } = dom;
// <ha-card> / <ha-icon> are unknown elements in jsdom: fine, they render as inline elements.
window.eval(source);

const nowIso = new Date().toISOString();
const twoHoursAgo = new Date(Date.now() - 2 * 3600 * 1000).toISOString();
const threeHoursAgo = new Date(Date.now() - 3 * 3600 * 1000).toISOString();

const overview = {
  tracking: true,
  version: "1.0.0",
  excel_available: true,
  total_records: 3,
  csv_path: "/config/suivi_presence_data.csv",
  load_error: null,
  data_range: { start_date: twoHoursAgo, end_date: nowIso, total_records: 3 },
  last_record: {
    timestamp: "2025-09-01T18:00:00+02:00",
    person: "Jean",
    previous_zone: "Travail",
    new_zone: "home",
  },
  persons: [
    {
      entity_id: "person.jean",
      name: "Jean",
      zone: "home",
      since: twoHoursAgo,
      available: true,
      latitude: 45.1,
      longitude: 3.2,
      gps_accuracy: 25,
      last_updated: threeHoursAgo, // stale (> 120 min)
    },
    { entity_id: "person.marie", name: "Marie", zone: "Travail", since: nowIso, available: false, latitude: null },
  ],
};

const history = {
  start: null,
  end: null,
  total: 3,
  truncated: true,
  records: [
    {
      timestamp: "2025-09-01T18:00:00+02:00",
      timestamp_utc: "2025-09-01T16:00:00+00:00",
      person: "Jean",
      previous_zone: "Travail",
      new_zone: "home",
      duration_seconds: 34200,
    },
    {
      timestamp: "2025-09-01T08:30:00+02:00",
      timestamp_utc: "2025-09-01T06:30:00+00:00",
      person: "Jean",
      previous_zone: "home",
      new_zone: "Travail",
      duration_seconds: 45000,
    },
  ],
  summary: {
    Jean: {
      home: { seconds: 50400, visits: 2, first: null, last: null, ongoing: true },
      Travail: { seconds: 36000, visits: 1, first: null, last: null, ongoing: false },
    },
  },
};

const calls = [];
const hass = {
  language: "fr",
  locale: { language: "fr" },
  states: {
    "person.jean": { state: "home", last_updated: threeHoursAgo, attributes: { friendly_name: "Jean" } },
    "person.marie": { state: "unavailable", last_updated: nowIso, attributes: { friendly_name: "Marie" } },
    "sensor.suivi_de_presence_total_des_changements": { state: "3", last_updated: nowIso, attributes: {} },
  },
  entities: {
    "sensor.suivi_de_presence_total_des_changements": { entity_id: "sensor.suivi_de_presence_total_des_changements", platform: "suivi_presence" },
  },
  hassUrl: (p) => `http://ha.local:8123${p}`,
  async callWS(msg) {
    calls.push(msg);
    if (msg.type === "suivi_presence/overview") return structuredClone(overview);
    if (msg.type === "suivi_presence/history") return structuredClone(history);
    if (msg.type === "auth/sign_path") return { path: `${msg.path}${msg.path.includes("?") ? "&" : "?"}authSig=signed` };
    throw new Error(`unexpected ws call ${msg.type}`);
  },
};

const tick = () => new Promise((resolve) => setTimeout(resolve, 20));
const text = (root) => root.textContent.replace(/\s+/g, " ").trim();

// --- render ------------------------------------------------------------------------
const card = window.document.createElement("suivi-presence-card");
card.setConfig({ title: "Test", default_period: "today", history_limit: 2 });
window.document.body.appendChild(card);
const notifications = [];
card.addEventListener("hass-notification", (e) => notifications.push(e.detail.message));
const moreInfo = [];
card.addEventListener("hass-more-info", (e) => moreInfo.push(e.detail.entityId));
card.hass = hass;
await tick();
await tick();

const root = card.shadowRoot;
assert.ok(root.querySelector("ha-card"), "ha-card rendered");
assert.equal(root.querySelector(".title").textContent, "Test");
assert.match(text(root.getElementById("header")), /Suivi actif · 2 personnes/);

// Persons: one row each, zone badges, since, GPS freshness, alerts.
const persons = [...root.querySelectorAll(".person")];
assert.equal(persons.length, 2);
assert.match(text(persons[0]), /Jean/);
assert.match(text(persons[0]), /Maison/);
assert.match(text(persons[0]), /depuis 2 h 00/);
assert.match(text(persons[0]), /Position ancienne/);
assert.match(text(persons[0]), /±25 m/);
assert.match(text(persons[1]), /Marie/);
assert.match(text(persons[1]), /Indisponible/);
assert.match(text(persons[1]), /Pas de position GPS/);
const alerts = text(root.getElementById("alerts"));
assert.match(alerts, /À vérifier/);
assert.match(alerts, /Marie : traqueur indisponible/);
assert.match(alerts, /Jean : position GPS non mise à jour/);

// Initial history request: today, limit from config.
const firstHistory = calls.find((c) => c.type === "suivi_presence/history");
assert.ok(firstHistory, "history requested");
assert.match(firstHistory.start, /^\d{4}-\d{2}-\d{2}$/);
assert.equal(firstHistory.end, undefined);
assert.equal(firstHistory.limit, 2);

// Summary + history rendering.
const summary = text(root.getElementById("summary"));
assert.match(summary, /Temps par zone/);
assert.match(summary, /Maison 14 h 00/);
assert.match(summary, /\(en cours\)/);
assert.match(summary, /2 passages/);
assert.equal(root.querySelectorAll(".seg").length, 2);
const hist = text(root.getElementById("history"));
assert.match(hist, /Changements de zone/);
assert.match(hist, /Travail/);
assert.match(hist, /après 9 h 30 à Travail/);
assert.match(hist, /2 sur 3 changements/);
assert.ok(root.querySelector('[data-action="more"]'), "show more button");
assert.equal(root.querySelectorAll(".hist-row").length, 2);

// Export bar sits right under the filters (before summary/history), then details.
const order = [...root.querySelectorAll(".card-content > div")].map((d) => d.id);
assert.deepEqual([...order], ["header", "alerts", "persons", "period", "export", "summary", "history", "details"]);
assert.match(text(root.getElementById("export")), /Exporter la période · Aujourd'hui/);
assert.equal(root.querySelector('[data-kind="excel"]').disabled, false);
assert.match(text(root.getElementById("details")), /suivi_presence_data\.csv/);
assert.match(text(root.getElementById("details")), /1\.0\.0/);

// HTML escaping of names.
overview.persons[0].name = "<img src=x onerror=alert(1)>";
card._overview = structuredClone(overview);
card._renderPersons();
assert.equal(root.querySelectorAll(".person img.avatar").length, 0, "no injected element");
assert.match(root.querySelector(".person .name").textContent, /<img/);
overview.persons[0].name = "Jean";

// --- interactions ---------------------------------------------------------------------
// Period chip 7d -> new history request with ISO start including offset.
calls.length = 0;
root.querySelector('[data-action="period"][data-period="7d"]').click();
await tick();
let req = calls.find((c) => c.type === "suivi_presence/history");
assert.ok(req);
assert.match(req.start, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/);
assert.ok(root.querySelector('[data-action="period"][data-period="7d"]').classList.contains("active"));

// "Tout" -> no bounds.
calls.length = 0;
root.querySelector('[data-action="period"][data-period="all"]').click();
await tick();
req = calls.find((c) => c.type === "suivi_presence/history");
assert.equal(req.start, undefined);
assert.equal(req.end, undefined);

// Person filter.
calls.length = 0;
root.querySelector('[data-action="person-toggle"][data-entity="person.marie"]').click();
await tick();
req = calls.find((c) => c.type === "suivi_presence/history");
assert.deepEqual([...req.persons], ["person.marie"]); // spread: array comes from the jsdom realm
root.querySelector('[data-action="person-all"]').click();
await tick();

// Show more increases the limit.
calls.length = 0;
root.querySelector('[data-action="more"]').click();
await tick();
req = calls.find((c) => c.type === "suivi_presence/history");
assert.equal(req.limit, 4);

// Custom period: inverted dates are swapped, dates sent as YYYY-MM-DD.
root.querySelector('[data-action="period"][data-period="custom"]').click();
await tick();
const startInput = root.getElementById("custom-start");
const endInput = root.getElementById("custom-end");
assert.ok(startInput && endInput, "date inputs rendered");
calls.length = 0;
startInput.value = "2025-09-10";
startInput.dispatchEvent(new window.Event("change", { bubbles: true, composed: true }));
endInput.value = "2025-09-01";
endInput.dispatchEvent(new window.Event("change", { bubbles: true, composed: true }));
await tick();
req = calls.filter((c) => c.type === "suivi_presence/history").pop();
assert.equal(req.start, "2025-09-01");
assert.equal(req.end, "2025-09-10");

// Downloads go through auth/sign_path and an <a download> element.
const clicked = [];
const origClick = window.HTMLAnchorElement.prototype.click;
window.HTMLAnchorElement.prototype.click = function () {
  clicked.push(this.href);
};
calls.length = 0;
root.querySelector('[data-action="download"][data-kind="csv"]').click();
await tick();
let sign = calls.find((c) => c.type === "auth/sign_path");
assert.ok(sign, "sign_path called for CSV");
assert.match(sign.path, /^\/api\/suivi_presence\/download\/csv\?start_date=2025-09-01&end_date=2025-09-10$/);
assert.equal(clicked.length, 1);
assert.match(clicked[0], /^http:\/\/ha\.local:8123\/api\/suivi_presence\/download\/csv\?.*authSig=signed$/);
assert.deepEqual(notifications.slice(-1), ["Téléchargement démarré"]);

calls.length = 0;
root.querySelector('[data-action="download"][data-kind="excel"]').click();
await tick();
sign = calls.find((c) => c.type === "auth/sign_path");
assert.match(sign.path, /^\/api\/suivi_presence\/download\/excel\?/);
assert.equal(clicked.length, 2);

// "Tout" + CSV -> full download endpoint.
root.querySelector('[data-action="period"][data-period="all"]').click();
await tick();
calls.length = 0;
root.querySelector('[data-action="download"][data-kind="csv"]').click();
await tick();
sign = calls.find((c) => c.type === "auth/sign_path");
assert.equal(sign.path, "/api/suivi_presence/download");
window.HTMLAnchorElement.prototype.click = origClick;

// Excel disabled when openpyxl is missing.
overview.excel_available = false;
card._overview = structuredClone(overview);
card._renderExport();
assert.equal(root.querySelector('[data-kind="excel"]').disabled, true);
assert.match(text(root.getElementById("export")), /Export Excel indisponible/);
overview.excel_available = true;

// Clicking a person fires hass-more-info with its entity id.
root.querySelector('.person[data-entity="person.jean"]').click();
assert.deepEqual(moreInfo, ["person.jean"]);

// Re-setting hass with unchanged states must not trigger new websocket calls.
calls.length = 0;
card.hass = { ...hass };
await new Promise((resolve) => setTimeout(resolve, 600));
assert.equal(calls.length, 0, "no refresh without relevant change");

// A changed person state schedules a (debounced) overview refresh.
card.hass = { ...hass, states: { ...hass.states, "person.jean": { ...hass.states["person.jean"], state: "not_home" } } };
await new Promise((resolve) => setTimeout(resolve, 600));
assert.ok(calls.some((c) => c.type === "suivi_presence/overview"), "overview refreshed after state change");

// Error path: integration not loaded.
const broken = window.document.createElement("suivi-presence-card");
broken.setConfig({});
window.document.body.appendChild(broken);
broken.hass = {
  ...hass,
  async callWS() {
    const err = new Error("not loaded");
    err.code = "not_loaded";
    throw err;
  },
};
await tick();
await tick();
assert.match(text(broken.shadowRoot.getElementById("alerts")), /n'est pas chargée/);

// English strings.
const en = window.document.createElement("suivi-presence-card");
en.setConfig({ title: "EN" });
window.document.body.appendChild(en);
en.hass = { ...hass, language: "en", locale: { language: "en" } };
await tick();
await tick();
assert.match(text(en.shadowRoot.getElementById("header")), /Tracking active · 2 persons/);

// Empty period: explain, recall the last change, offer to widen the period.
const emptyCard = window.document.createElement("suivi-presence-card");
emptyCard.setConfig({ title: "Empty", default_period: "today" });
window.document.body.appendChild(emptyCard);
const emptyCalls = [];
emptyCard.hass = {
  ...hass,
  async callWS(msg) {
    emptyCalls.push(msg);
    if (msg.type === "suivi_presence/overview") return structuredClone(overview);
    if (msg.type === "suivi_presence/history") return { start: null, end: null, total: 0, truncated: false, records: [], summary: {} };
    throw new Error("unexpected");
  },
};
await tick();
await tick();
const emptyText = text(emptyCard.shadowRoot.getElementById("history"));
assert.match(emptyText, /Aucun changement de zone depuis minuit/);
assert.match(emptyText, /Dernier changement enregistré : 01\/09\/2025 \d{2}:\d{2} — Jean, Travail → Maison/);
assert.match(emptyText, /3 enregistrements au total/);
const widen = emptyCard.shadowRoot.querySelector('#history [data-action="period"][data-period="7d"]');
assert.ok(widen, "widen chip offered");
emptyCalls.length = 0;
widen.click();
await tick();
assert.equal(emptyCalls.find((c) => c.type === "suivi_presence/history")?.start?.length, 25);
assert.ok(emptyCard.shadowRoot.querySelector('#period [data-period="7d"]').classList.contains("active"));

// The chosen period is remembered per browser and restored by a new card instance
// with the same config; a different configured default starts fresh.
assert.ok(window.localStorage.getItem("suivi-presence-card:Empty:today"), "period saved");
const restored = window.document.createElement("suivi-presence-card");
restored.setConfig({ title: "Empty", default_period: "today" });
assert.equal(restored._period, "7d");
const fresh = window.document.createElement("suivi-presence-card");
fresh.setConfig({ title: "Empty", default_period: "30d" });
assert.equal(fresh._period, "30d");

// Config validation.
assert.throws(() => window.document.createElement("suivi-presence-card").setConfig({ default_period: "yesterday" }));
assert.throws(() => window.document.createElement("suivi-presence-card").setConfig({ persons: "person.jean" }));

// customCards registration.
assert.ok(window.customCards.some((c) => c.type === "suivi-presence-card"));

console.log("card tests: OK");
// The cards keep 60 s refresh timers alive: close the window and exit explicitly.
window.close();
process.exit(0);
