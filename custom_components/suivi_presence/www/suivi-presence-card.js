/**
 * Suivi de Présence - Custom Lovelace Card
 * Version: 0.0.1
 *
 * This card displays presence tracking information and provides
 * a download button for the CSV export.
 */

class SuiviPresenceCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  setConfig(config) {
    this._config = config;
  }

  getCardSize() {
    return 4;
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
    const showHistory = config.show_history !== false;
    const historyCount = config.history_count || 10;

    // Find the main sensor
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

    // Build the card HTML
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
        }

        .title {
          font-size: 1.2em;
          font-weight: 500;
          color: var(--primary-text-color);
        }

        .download-btn {
          background: var(--primary-color);
          color: var(--text-primary-color, white);
          border: none;
          border-radius: 4px;
          padding: 8px 16px;
          cursor: pointer;
          font-size: 0.9em;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .download-btn:hover {
          opacity: 0.9;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
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
          font-size: 2em;
          font-weight: bold;
          color: var(--primary-color);
        }

        .stat-label {
          font-size: 0.85em;
          color: var(--secondary-text-color);
          margin-top: 4px;
        }

        .stat-card.home .stat-value {
          color: var(--success-color, #4caf50);
        }

        .stat-card.away .stat-value {
          color: var(--warning-color, #ff9800);
        }

        .persons-section {
          margin-bottom: 16px;
        }

        .section-title {
          font-weight: 500;
          margin-bottom: 8px;
          color: var(--primary-text-color);
        }

        .persons-list {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .person-badge {
          background: var(--secondary-background-color);
          border-radius: 16px;
          padding: 4px 12px;
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
          font-size: 0.85em;
        }

        .history-table th,
        .history-table td {
          padding: 8px;
          text-align: left;
          border-bottom: 1px solid var(--divider-color);
        }

        .history-table th {
          background: var(--secondary-background-color);
          font-weight: 500;
        }

        .history-table tr:hover {
          background: var(--secondary-background-color);
        }

        .no-data {
          text-align: center;
          color: var(--secondary-text-color);
          padding: 20px;
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
      </style>

      <ha-card>
        <div class="header">
          <span class="title">${title}</span>
          <button class="download-btn" id="download-btn">
            <ha-icon icon="mdi:download"></ha-icon>
            Télécharger CSV
          </button>
        </div>

        <div class="stats-grid">
          <div class="stat-card home">
            <div class="stat-value">${personsHomeSensor ? personsHomeSensor.state : "0"}</div>
            <div class="stat-label">À domicile</div>
          </div>
          <div class="stat-card away">
            <div class="stat-value">${personsAwaySensor ? personsAwaySensor.state : "0"}</div>
            <div class="stat-label">Absents</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${totalChangesSensor ? totalChangesSensor.state : "0"}</div>
            <div class="stat-label">Changements</div>
          </div>
        </div>

        ${this._renderPersonsSection(mainSensor)}

        ${showHistory ? this._renderHistorySection(mainSensor, historyCount) : ""}
      </ha-card>
    `;

    // Add download button event listener
    this.shadowRoot.getElementById("download-btn").addEventListener("click", () => {
      this._downloadCSV();
    });
  }

  _renderPersonsSection(mainSensor) {
    if (!mainSensor) {
      return '<div class="no-data">Aucune donnée disponible</div>';
    }

    const attrs = mainSensor.attributes;
    const personsHome = attrs.persons_home || [];
    const personsAway = attrs.persons_away || [];
    const personsInZones = attrs.persons_in_zones || [];

    return `
      <div class="persons-section">
        <div class="section-title">Personnes à domicile</div>
        <div class="persons-list">
          ${
            personsHome.length > 0
              ? personsHome
                  .map(
                    (p) =>
                      `<span class="person-badge home"><ha-icon icon="mdi:home-account"></ha-icon>${p}</span>`
                  )
                  .join("")
              : '<span class="no-data">Personne</span>'
          }
        </div>
      </div>

      <div class="persons-section">
        <div class="section-title">Personnes absentes</div>
        <div class="persons-list">
          ${
            personsAway.length > 0
              ? personsAway
                  .map(
                    (p) =>
                      `<span class="person-badge away"><ha-icon icon="mdi:home-export-outline"></ha-icon>${p}</span>`
                  )
                  .join("")
              : '<span class="no-data">Personne</span>'
          }
        </div>
      </div>

      ${
        personsInZones.length > 0
          ? `
        <div class="persons-section">
          <div class="section-title">Dans d'autres zones</div>
          <div class="persons-list">
            ${personsInZones
              .map(
                (p) =>
                  `<span class="person-badge zone"><ha-icon icon="mdi:map-marker"></ha-icon>${p}</span>`
              )
              .join("")}
          </div>
        </div>
      `
          : ""
      }
    `;
  }

  _renderHistorySection(mainSensor, count) {
    // For history, we need to fetch from the API
    // For now, show the last change info
    if (!mainSensor) {
      return "";
    }

    const lastChange = mainSensor.attributes.last_change;

    return `
      <div class="history-section">
        <div class="section-title">Dernier changement</div>
        ${
          lastChange
            ? `<p>${lastChange}</p>`
            : '<div class="no-data">Aucun changement enregistré</div>'
        }
        <p style="font-size: 0.85em; color: var(--secondary-text-color);">
          Téléchargez le CSV pour voir l'historique complet.
        </p>
      </div>
    `;
  }

  _downloadCSV() {
    // Create a link to download the CSV
    const link = document.createElement("a");
    link.href = "/api/suivi_presence/download";
    link.download = "suivi_presence.csv";
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
  description: "Carte affichant le suivi des présences avec export CSV",
  preview: true,
});

console.info(
  "%c SUIVI-PRESENCE-CARD %c 0.0.1 ",
  "color: white; background: #3498db; font-weight: bold;",
  "color: #3498db; background: white; font-weight: bold;"
);
