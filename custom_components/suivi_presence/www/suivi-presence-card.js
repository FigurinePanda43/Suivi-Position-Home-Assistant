/**
 * Suivi de Présence - Custom Lovelace Card
 * Version: 0.1.0
 *
 * This card displays presence tracking information and provides
 * download buttons for CSV and Excel exports with filtering options.
 */

class SuiviPresenceCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._filterOpen = false;
    this._startDate = "";
    this._endDate = "";
    this._selectedPersons = [];
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this.render();
      this._rendered = true;
    } else {
      this._updateData();
    }
  }

  setConfig(config) {
    this._config = config;
  }

  getCardSize() {
    return 5;
  }

  static getConfigElement() {
    return document.createElement("suivi-presence-card-editor");
  }

  static getStubConfig() {
    return {
      title: "Suivi de Présence",
      show_history: true,
      history_count: 10,
    };
  }

  render() {
    if (!this._hass) return;

    const config = this._config || {};
    const title = config.title || "Suivi de Présence";

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          --card-primary-color: var(--primary-color);
          --card-background: var(--ha-card-background, var(--card-background-color, white));
        }

        ha-card {
          padding: 16px;
        }

        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          flex-wrap: wrap;
          gap: 8px;
        }

        .title {
          font-size: 1.2em;
          font-weight: 500;
          color: var(--primary-text-color);
        }

        .buttons-row {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        .btn {
          background: var(--primary-color);
          color: var(--text-primary-color, white);
          border: none;
          border-radius: 4px;
          padding: 8px 12px;
          cursor: pointer;
          font-size: 0.85em;
          display: flex;
          align-items: center;
          gap: 6px;
          transition: opacity 0.2s;
        }

        .btn:hover {
          opacity: 0.85;
        }

        .btn.secondary {
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          border: 1px solid var(--divider-color);
        }

        .btn.excel {
          background: #217346;
        }

        .btn.filter {
          background: var(--accent-color, #ff9800);
        }

        .filter-panel {
          display: none;
          background: var(--secondary-background-color);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 16px;
        }

        .filter-panel.open {
          display: block;
        }

        .filter-row {
          display: flex;
          gap: 12px;
          margin-bottom: 12px;
          flex-wrap: wrap;
          align-items: flex-end;
        }

        .filter-group {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .filter-group label {
          font-size: 0.85em;
          color: var(--secondary-text-color);
        }

        .filter-group input,
        .filter-group select {
          padding: 8px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font-size: 0.9em;
        }

        .filter-group select {
          min-width: 150px;
        }

        .persons-checkboxes {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 8px;
        }

        .person-checkbox {
          display: flex;
          align-items: center;
          gap: 4px;
          background: var(--card-background-color);
          padding: 4px 8px;
          border-radius: 4px;
          border: 1px solid var(--divider-color);
          cursor: pointer;
        }

        .person-checkbox:hover {
          background: var(--secondary-background-color);
        }

        .person-checkbox input {
          cursor: pointer;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
          gap: 12px;
          margin-bottom: 16px;
        }

        .stat-card {
          background: var(--secondary-background-color);
          border-radius: 8px;
          padding: 12px;
          text-align: center;
        }

        .stat-value {
          font-size: 1.8em;
          font-weight: bold;
          color: var(--primary-color);
        }

        .stat-label {
          font-size: 0.8em;
          color: var(--secondary-text-color);
          margin-top: 4px;
        }

        .stat-card.home .stat-value {
          color: var(--success-color, #4caf50);
        }

        .stat-card.away .stat-value {
          color: var(--warning-color, #ff9800);
        }

        .stat-card.records .stat-value {
          color: var(--info-color, #2196f3);
        }

        .persons-section {
          margin-bottom: 16px;
        }

        .section-title {
          font-weight: 500;
          margin-bottom: 8px;
          color: var(--primary-text-color);
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .persons-list {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .person-badge {
          background: var(--secondary-background-color);
          border-radius: 16px;
          padding: 6px 12px;
          font-size: 0.9em;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .person-badge.home {
          border-left: 3px solid var(--success-color, #4caf50);
        }

        .person-badge.away {
          border-left: 3px solid var(--warning-color, #ff9800);
        }

        .person-badge.zone {
          border-left: 3px solid var(--info-color, #2196f3);
        }

        .history-section {
          margin-top: 16px;
        }

        .history-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.8em;
        }

        .history-table th,
        .history-table td {
          padding: 8px 6px;
          text-align: left;
          border-bottom: 1px solid var(--divider-color);
        }

        .history-table th {
          background: var(--secondary-background-color);
          font-weight: 500;
          position: sticky;
          top: 0;
        }

        .history-table tr:hover {
          background: var(--secondary-background-color);
        }

        .history-container {
          max-height: 300px;
          overflow-y: auto;
        }

        .no-data {
          text-align: center;
          color: var(--secondary-text-color);
          padding: 20px;
          font-style: italic;
        }

        .data-range {
          font-size: 0.8em;
          color: var(--secondary-text-color);
          margin-top: 8px;
          padding: 8px;
          background: var(--secondary-background-color);
          border-radius: 4px;
        }

        .zone-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 0.85em;
        }

        .zone-badge.home {
          background: rgba(76, 175, 80, 0.2);
          color: var(--success-color, #4caf50);
        }

        .zone-badge.not_home {
          background: rgba(255, 152, 0, 0.2);
          color: var(--warning-color, #ff9800);
        }

        .zone-badge.other {
          background: rgba(33, 150, 243, 0.2);
          color: var(--info-color, #2196f3);
        }

        @media (max-width: 500px) {
          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }
          .filter-row {
            flex-direction: column;
          }
          .filter-group {
            width: 100%;
          }
          .filter-group input,
          .filter-group select {
            width: 100%;
          }
        }
      </style>

      <ha-card>
        <div class="header">
          <span class="title">${title}</span>
          <div class="buttons-row">
            <button class="btn filter" id="filter-btn">
              <ha-icon icon="mdi:filter"></ha-icon>
              Filtres
            </button>
            <button class="btn secondary" id="csv-btn">
              <ha-icon icon="mdi:file-delimited"></ha-icon>
              CSV
            </button>
            <button class="btn excel" id="excel-btn">
              <ha-icon icon="mdi:microsoft-excel"></ha-icon>
              Excel
            </button>
          </div>
        </div>

        <div class="filter-panel" id="filter-panel">
          <div class="filter-row">
            <div class="filter-group">
              <label>Date de début</label>
              <input type="date" id="start-date" />
            </div>
            <div class="filter-group">
              <label>Date de fin</label>
              <input type="date" id="end-date" />
            </div>
            <button class="btn secondary" id="clear-filters">
              <ha-icon icon="mdi:close"></ha-icon>
              Effacer
            </button>
          </div>
          <div class="filter-group">
            <label>Personnes à inclure (vide = toutes)</label>
            <div class="persons-checkboxes" id="persons-checkboxes">
              <!-- Populated dynamically -->
            </div>
          </div>
        </div>

        <div class="stats-grid" id="stats-grid">
          <!-- Populated dynamically -->
        </div>

        <div id="persons-content">
          <!-- Populated dynamically -->
        </div>

        <div class="data-range" id="data-range">
          <!-- Populated dynamically -->
        </div>

        <div class="history-section">
          <div class="section-title">
            <ha-icon icon="mdi:history"></ha-icon>
            Historique récent
          </div>
          <div class="history-container">
            <table class="history-table">
              <thead>
                <tr>
                  <th>Date/Heure</th>
                  <th>Personne</th>
                  <th>De</th>
                  <th>Vers</th>
                </tr>
              </thead>
              <tbody id="history-body">
                <!-- Populated dynamically -->
              </tbody>
            </table>
          </div>
        </div>
      </ha-card>
    `;

    // Add event listeners
    this._setupEventListeners();
    this._updateData();
  }

  _setupEventListeners() {
    // Filter toggle
    this.shadowRoot.getElementById("filter-btn").addEventListener("click", () => {
      this._filterOpen = !this._filterOpen;
      this.shadowRoot
        .getElementById("filter-panel")
        .classList.toggle("open", this._filterOpen);
    });

    // Clear filters
    this.shadowRoot.getElementById("clear-filters").addEventListener("click", () => {
      this.shadowRoot.getElementById("start-date").value = "";
      this.shadowRoot.getElementById("end-date").value = "";
      this._startDate = "";
      this._endDate = "";
      this._selectedPersons = [];
      this._updatePersonCheckboxes();
    });

    // Date inputs
    this.shadowRoot.getElementById("start-date").addEventListener("change", (e) => {
      this._startDate = e.target.value;
    });

    this.shadowRoot.getElementById("end-date").addEventListener("change", (e) => {
      this._endDate = e.target.value;
    });

    // CSV download
    this.shadowRoot.getElementById("csv-btn").addEventListener("click", () => {
      this._downloadCSV();
    });

    // Excel download
    this.shadowRoot.getElementById("excel-btn").addEventListener("click", () => {
      this._downloadExcel();
    });
  }

  _updateData() {
    // Find sensors
    const mainSensor = Object.values(this._hass.states).find(
      (s) =>
        s.entity_id.startsWith("sensor.suivi_presence") &&
        s.entity_id.endsWith("_main")
    );

    const personsHomeSensor = Object.values(this._hass.states).find(
      (s) =>
        s.entity_id.startsWith("sensor.suivi_presence") &&
        s.entity_id.includes("personnes_a_domicile")
    );

    const personsAwaySensor = Object.values(this._hass.states).find(
      (s) =>
        s.entity_id.startsWith("sensor.suivi_presence") &&
        s.entity_id.includes("personnes_absentes")
    );

    const totalChangesSensor = Object.values(this._hass.states).find(
      (s) =>
        s.entity_id.startsWith("sensor.suivi_presence") &&
        s.entity_id.includes("total_des_changements")
    );

    // Update stats
    const statsGrid = this.shadowRoot.getElementById("stats-grid");
    const personsHome = personsHomeSensor ? personsHomeSensor.state : "0";
    const personsAway = personsAwaySensor ? personsAwaySensor.state : "0";
    const totalChanges = totalChangesSensor ? totalChangesSensor.state : "0";

    statsGrid.innerHTML = `
      <div class="stat-card home">
        <div class="stat-value">${personsHome}</div>
        <div class="stat-label">À domicile</div>
      </div>
      <div class="stat-card away">
        <div class="stat-value">${personsAway}</div>
        <div class="stat-label">Absents</div>
      </div>
      <div class="stat-card records">
        <div class="stat-value">${totalChanges}</div>
        <div class="stat-label">Enregistrements</div>
      </div>
    `;

    // Update persons content
    this._updatePersonsContent(mainSensor);

    // Update persons checkboxes for filtering
    this._updatePersonCheckboxes(mainSensor);

    // Update data range info
    this._updateDataRange(mainSensor);

    // Update history
    this._updateHistory(mainSensor);
  }

  _updatePersonsContent(mainSensor) {
    const container = this.shadowRoot.getElementById("persons-content");

    if (!mainSensor) {
      container.innerHTML = '<div class="no-data">En attente de données...</div>';
      return;
    }

    const attrs = mainSensor.attributes;
    const personsHome = attrs.persons_home || [];
    const personsAway = attrs.persons_away || [];
    const personsInZones = attrs.persons_in_zones || {};

    let html = "";

    // Persons at home
    html += `
      <div class="persons-section">
        <div class="section-title">
          <ha-icon icon="mdi:home-account"></ha-icon>
          À domicile
        </div>
        <div class="persons-list">
          ${
            personsHome.length > 0
              ? personsHome
                  .map((p) => `<span class="person-badge home">${p}</span>`)
                  .join("")
              : '<span class="no-data">Personne</span>'
          }
        </div>
      </div>
    `;

    // Persons away
    html += `
      <div class="persons-section">
        <div class="section-title">
          <ha-icon icon="mdi:home-export-outline"></ha-icon>
          Absents
        </div>
        <div class="persons-list">
          ${
            personsAway.length > 0
              ? personsAway
                  .map((p) => `<span class="person-badge away">${p}</span>`)
                  .join("")
              : '<span class="no-data">Personne</span>'
          }
        </div>
      </div>
    `;

    // Persons in other zones
    if (Object.keys(personsInZones).length > 0) {
      html += `
        <div class="persons-section">
          <div class="section-title">
            <ha-icon icon="mdi:map-marker"></ha-icon>
            Autres zones
          </div>
          <div class="persons-list">
            ${Object.entries(personsInZones)
              .map(
                ([person, zone]) =>
                  `<span class="person-badge zone">${person} (${zone})</span>`
              )
              .join("")}
          </div>
        </div>
      `;
    }

    container.innerHTML = html;
  }

  _updatePersonCheckboxes(mainSensor) {
    const container = this.shadowRoot.getElementById("persons-checkboxes");

    // Get all persons from main sensor
    let allPersons = [];
    if (mainSensor && mainSensor.attributes) {
      const attrs = mainSensor.attributes;
      allPersons = [
        ...(attrs.persons_home || []),
        ...(attrs.persons_away || []),
        ...Object.keys(attrs.persons_in_zones || {}),
      ];
      allPersons = [...new Set(allPersons)].sort();
    }

    if (allPersons.length === 0) {
      container.innerHTML = '<span class="no-data">Aucune personne détectée</span>';
      return;
    }

    container.innerHTML = allPersons
      .map(
        (person) => `
        <label class="person-checkbox">
          <input type="checkbox" value="${person}"
            ${this._selectedPersons.includes(person) ? "checked" : ""} />
          ${person}
        </label>
      `
      )
      .join("");

    // Add event listeners to checkboxes
    container.querySelectorAll("input[type=checkbox]").forEach((cb) => {
      cb.addEventListener("change", (e) => {
        if (e.target.checked) {
          if (!this._selectedPersons.includes(e.target.value)) {
            this._selectedPersons.push(e.target.value);
          }
        } else {
          this._selectedPersons = this._selectedPersons.filter(
            (p) => p !== e.target.value
          );
        }
      });
    });
  }

  _updateDataRange(mainSensor) {
    const container = this.shadowRoot.getElementById("data-range");

    if (!mainSensor || !mainSensor.attributes) {
      container.innerHTML = "Aucune donnée disponible";
      return;
    }

    const dataRange = mainSensor.attributes.data_range;
    if (!dataRange || !dataRange.start_date) {
      container.innerHTML = "Aucun historique enregistré";
      return;
    }

    const startDate = new Date(dataRange.start_date).toLocaleDateString("fr-FR");
    const endDate = new Date(dataRange.end_date).toLocaleDateString("fr-FR");

    container.innerHTML = `
      <strong>Données disponibles:</strong> du ${startDate} au ${endDate}
      (${dataRange.total_records} enregistrements,
      ${dataRange.unique_persons?.length || 0} personnes,
      ${dataRange.unique_zones?.length || 0} zones)
    `;
  }

  _updateHistory(mainSensor) {
    const tbody = this.shadowRoot.getElementById("history-body");

    if (!mainSensor || !mainSensor.attributes) {
      tbody.innerHTML =
        '<tr><td colspan="4" class="no-data">Aucun historique</td></tr>';
      return;
    }

    const history = mainSensor.attributes.recent_history || [];

    if (history.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="4" class="no-data">Aucun mouvement enregistré</td></tr>';
      return;
    }

    // Show last 10 entries, most recent first
    const recentHistory = history.slice(-10).reverse();

    tbody.innerHTML = recentHistory
      .map((record) => {
        const timestamp = new Date(record.timestamp);
        const formattedDate = timestamp.toLocaleDateString("fr-FR");
        const formattedTime = timestamp.toLocaleTimeString("fr-FR", {
          hour: "2-digit",
          minute: "2-digit",
        });

        const fromZoneClass =
          record.previous_zone === "home"
            ? "home"
            : record.previous_zone === "not_home"
            ? "not_home"
            : "other";
        const toZoneClass =
          record.new_zone === "home"
            ? "home"
            : record.new_zone === "not_home"
            ? "not_home"
            : "other";

        return `
          <tr>
            <td>${formattedDate} ${formattedTime}</td>
            <td>${record.person}</td>
            <td><span class="zone-badge ${fromZoneClass}">${record.previous_zone}</span></td>
            <td><span class="zone-badge ${toZoneClass}">${record.new_zone}</span></td>
          </tr>
        `;
      })
      .join("");
  }

  _buildQueryParams() {
    const params = new URLSearchParams();

    if (this._startDate) {
      params.append("start_date", this._startDate + "T00:00:00");
    }

    if (this._endDate) {
      params.append("end_date", this._endDate + "T23:59:59");
    }

    if (this._selectedPersons.length > 0) {
      params.append("persons", this._selectedPersons.join(","));
    }

    return params.toString();
  }

  _downloadCSV() {
    const queryParams = this._buildQueryParams();
    const url = queryParams
      ? `/api/suivi_presence/download/csv?${queryParams}`
      : "/api/suivi_presence/download";

    const link = document.createElement("a");
    link.href = url;
    link.download = "suivi_presence.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  _downloadExcel() {
    const queryParams = this._buildQueryParams();
    const url = `/api/suivi_presence/download/excel${
      queryParams ? "?" + queryParams : ""
    }`;

    const link = document.createElement("a");
    link.href = url;
    link.download = "suivi_presence.xlsx";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

// Define the custom element
customElements.define("suivi-presence-card", SuiviPresenceCard);

// Register the card with HACS/Lovelace
window.customCards = window.customCards || [];
window.customCards.push({
  type: "suivi-presence-card",
  name: "Suivi de Présence",
  description:
    "Carte affichant le suivi des présences avec export CSV et Excel filtrable",
  preview: true,
});

console.info(
  "%c SUIVI-PRESENCE-CARD %c 0.1.0 ",
  "color: white; background: #3498db; font-weight: bold;",
  "color: #3498db; background: white; font-weight: bold;"
);
