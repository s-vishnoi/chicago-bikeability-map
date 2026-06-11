const DEFAULT_SEVERITY_FILTERS = ["fatal", "severe"];

const state = {
  data: null,
  areas: [],
  selected: null,
  hovered: null,
  crashFilters: {
    severities: [...DEFAULT_SEVERITY_FILTERS],
    cause: null,
  },
  hoverEnabled: false,
  firstSelectionDone: false,
  hoverTimer: null,
};

const FLIP_MS = 720;

const svg = document.querySelector("#atlas-map");
const tileLayer = document.querySelector("#tile-layer");
const lakeLayer = document.querySelector("#city-outline");
const search = document.querySelector("#area-search");
const datalist = document.querySelector("#area-list");
const panelContent = document.querySelector("#panel-content");
const networkPanelContent = document.querySelector("#network-panel-content");
const networkMapDockContent = document.querySelector("#network-map-dock-content");
const hoverSpotlight = document.querySelector("#hover-spotlight");

const injuryLabels = [
  ["FATAL", "Fatal", "fatal"],
  ["INCAPACITATING INJURY", "Incapacitating", "severe"],
  ["NONINCAPACITATING INJURY", "Non-incapacitating", "moderate"],
  ["REPORTED, NOT EVIDENT", "Reported", "reported"],
  ["NO INDICATION OF INJURY", "No injury", "none"],
];

const laneTypes = [
  ["Protected", "protected"],
  ["Neighborhood", "neighborhood"],
  ["Buffered", "buffered"],
  ["Painted", "painted"],
  ["Shared", "shared"],
];

const laneLabelToDataKey = {
  Protected: "Protected",
  Neighborhood: "Local",
  Buffered: "Buffered",
  Painted: "Painted",
  Shared: "Shared",
};

function laneMiles(area, label) {
  const dataKey = laneLabelToDataKey[label] || label;
  return Number(area?.laneMiles?.[dataKey] ?? area?.laneMiles?.[label] ?? 0);
}

function laneShare(area, label) {
  const total = Number(area?.laneTotal || 0);
  if (!total) return 0;
  return (laneMiles(area, label) / total) * 100;
}

const PLOT = {
  cell: 64,
  tile: 61,
  originX: -20,
  originY: -54,
};

function fmt(value, digits = 0) {
  return Number(value || 0).toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function starString(rank) {
  return "✶".repeat(clamp(Math.round(rank) + 1, 1, 5));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function showInitialTip() {
  if (state.firstSelectionDone || document.querySelector(".guiding-tip")) return;
  const tip = document.createElement("div");
  tip.className = "guiding-tip";
  tip.textContent = "Click on a community to explore the map!";
  document.body.appendChild(tip);
}

function hideInitialTip() {
  document.querySelector(".guiding-tip")?.remove();
}

function colorFor(area) {
  return area.bikeRank >= 2 ? "#2f8cc8" : "#ff9caf";
}

function injuryBreakdown(area) {
  return injuryLabels
    .map(([key, label, cls]) => ({
      key,
      label,
      cls,
      value: Number(area?.injuries?.[key] || 0),
    }))
    .filter((item) => item.value > 0);
}

function injuryTotal(area) {
  return Object.values(area?.injuries || {}).reduce((sum, count) => sum + Number(count || 0), 0);
}

function severeInjuryCount(area) {
  return crashSeverityCount(area, "fatal") + crashSeverityCount(area, "severe");
}

function severeInjuryShare(area) {
  const total = Number(area?.totalCrashes || 0) || injuryTotal(area);
  if (!total) return 0;
  return severeInjuryCount(area) / total;
}

function injuryDropCount(area) {
  const severeSharePct = severeInjuryShare(area) * 100;
  return clamp(Math.ceil(severeSharePct / 5), 0, 5);
}

function causeBreakdown(area) {
  return (area?.topCauses || []).slice(0, 5).map((cause) => ({
    key: normalizeFilterValue(cause.name),
    label: cause.name,
    count: Number(cause.count || 0),
  }));
}

function titleCase(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\b[a-z]/g, (match) => match.toUpperCase())
    .trim();
}

function severityKey(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (normalized === "fatal") return "fatal";
  if (normalized === "severe") return "severe";
  if (normalized === "incapacitating injury") return "severe";
  if (normalized === "moderate") return "moderate";
  if (normalized === "nonincapacitating injury") return "moderate";
  if (normalized === "reported") return "reported";
  if (normalized === "reported, not evident") return "reported";
  if (normalized === "none") return "none";
  if (normalized === "no indication of injury") return "none";
  return "unknown";
}

function normalizeFilterValue(value) {
  return String(value || "").trim().toLowerCase();
}

function activeSeverityKeys() {
  const severities = state.crashFilters?.severities;
  if (Array.isArray(severities)) return severities;
  const legacySeverity = state.crashFilters?.severity;
  return legacySeverity ? [legacySeverity] : [...DEFAULT_SEVERITY_FILTERS];
}

const crashSeverityOptions = [
  {
    key: "fatal",
    label: "Fatal",
    markerLabel: "Red",
    cls: "fatal",
  },
  {
    key: "severe",
    label: "Incapacitating injury",
    markerLabel: "Yellow",
    cls: "severe",
  },

  {
    key: "moderate",
    label: "Non-incapacitating injury",
    markerLabel: "Light pink",
    cls: "moderate",
  },
  {
    key: "reported",
    label: "Reported, not evident",
    markerLabel: "Gray",
    cls: "reported",
  },
  {
    key: "none",
    label: "No indication of injury",
    markerLabel: "Light",
    cls: "none",
  },
];

function buildBikeabilityHelpButton() {
  return `
    <div class="bikeability-link-stack">
      <a class="bikeability-meta-link" href="https://www.vishnoi.site" target="_blank" rel="noopener noreferrer">@vishnoi</a>
      <a class="bikeability-meta-link" href="https://github.com/s-vishnoi/chicago-bikeability-map" target="_blank" rel="noopener noreferrer">@github</a>
      <button class="bikeability-help-btn" type="button" onclick="document.getElementById('bikeability-help-modal').classList.add('is-visible')">Bikeability?</button>
    </div>
  `;
}

function buildBikeabilityLegend() {
  return `
    <div class="bikeability-legend" style="display: flex; flex-direction: column; gap: 12px;">
      <div style="font-size: 12px; font-weight: 500; color: #f4f4f4; text-transform: uppercase;">How to Read the Map</div>
      <div style="display: flex; align-items: center; gap: 16px;">
        <svg width="100" height="100" viewBox="0 0 60 60" style="overflow: visible;">
          <rect width="30" height="60" rx="0" fill="#ff9caf" stroke="none" />
          <rect x="30" width="30" height="60" rx="0" fill="#2f8cc8" stroke="none" />
          <rect width="60" height="60" rx="0" fill="none" stroke="rgba(128, 128, 128, 0.5)" stroke-width="1" />
          <rect x="-3" y="3" width="66" height="15" fill="rgba(0, 0, 0, 0.4)" stroke="none" />
          <text x="30" y="14" fill="#ffffff" font-size="6px" font-weight="800" text-anchor="middle" pointer-events="none">COMMUNITY</text>
          
          <text x="30" y="33.2" fill="#f2f2f2" font-size="10px" font-weight="700" text-anchor="middle" pointer-events="none">✶✶✶</text>

          <g transform="translate(17.1, 49) scale(0.456)">
            <path d="M 5 0 C 5 0, 0 8, 0 11 A 5 5 0 1 0 10 11 C 10 8, 5 0, 5 0 Z" fill="var(--red)" opacity="0.5"></path>
            <path d="M 5 0 C 5 0, 0 8, 0 11 A 5 5 0 1 0 10 11 C 10 8, 5 0, 5 0 Z" fill="var(--red)" opacity="0.5" transform="translate(11, 0)"></path>
            <path d="M 5 0 C 5 0, 0 8, 0 11 A 5 5 0 1 0 10 11 C 10 8, 5 0, 5 0 Z" fill="var(--red)" opacity="0.5" transform="translate(22, 0)"></path>
            <path d="M 5 0 C 5 0, 0 8, 0 11 A 5 5 0 1 0 10 11 C 10 8, 5 0, 5 0 Z" fill="transparent" transform="translate(33, 0)"></path>
            <path d="M 5 0 C 5 0, 0 8, 0 11 A 5 5 0 1 0 10 11 C 10 8, 5 0, 5 0 Z" fill="transparent" transform="translate(44, 0)"></path>
          </g>
        </svg>
        
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <div style="font-size: 10px; color: rgba(244,244,244,0.8); line-height: 1.3;">
            <span style="display: inline-block; width: 8px; height: 8px; background: #ff9caf; border-radius: 0; margin-right: 4px; vertical-align: middle;"></span>
            <strong>Pink:</strong> Below median bikeability
          </div>
          <div style="font-size: 10px; color: rgba(244,244,244,0.8); line-height: 1.3;">
            <span style="display: inline-block; width: 8px; height: 8px; background: #2f8cc8; border-radius: 0; margin-right: 4px; vertical-align: middle;"></span>
            <strong>Blue:</strong> Median or higher bikeability
          </div>
          <div style="font-size: 10px; color: rgba(244,244,244,0.8); line-height: 1.3; margin-top: 2px;">
            <span style="color: #f2f2f2; font-size: 12px; margin-right: 4px; vertical-align: middle; display: inline-block; text-align: center; width: 8px;">★</span>
            <strong>Stars:</strong> Bikeability ranking /5
          </div>
          <div style="font-size: 10px; color: rgba(244,244,244,0.8); line-height: 1.3; margin-top: 2px;">
            <svg width="5" height="6" viewBox="0 0 10 11" style="display: inline-block; vertical-align: middle; margin-right: 4px; overflow: visible;">
              <path d="M 5 0 C 5 0, 0 8, 0 11 A 5 5 0 1 0 10 11 C 10 8, 5 0, 5 0 Z" fill="var(--red)" opacity="0.5"></path>
            </svg>
            <strong>Drop:</strong> Severe injury risk (fatal/incapacitating)
          </div>
        </div>
      </div>
    </div>
  `;
}

function crashSeverityCount(area, key) {
  const canonicalKey = severityKey(key);
  return Object.entries(area?.injuries || {}).reduce((sum, [injuryKey, count]) => {
    if (severityKey(injuryKey) !== canonicalKey) return sum;
    return sum + Number(count || 0);
  }, 0);
}

function buildSeverityRows(area, animate = false) {
  const total = crashSeverityOptions.reduce((sum, item) => sum + crashSeverityCount(area, item.key), 0) || 1;
  const activeSeverities = activeSeverityKeys();

  return crashSeverityOptions.map((item, index) => {
    const count = crashSeverityCount(area, item.key);
    const share = (count / total) * 100;
    const width = Math.max(3, share);
    const isActive = activeSeverities.includes(item.key);
    return `
      <button
        type="button"
        class="crash-row severity-row severity-row-${item.cls} ${animate ? "is-animated" : ""} ${isActive ? "is-active" : ""}"
        style="--severity-delay:${index * 48}ms; --share:${width}%;"
        data-crash-severity="${escapeHtml(item.key)}"
        aria-pressed="${isActive ? "true" : "false"}"
      >
        <div class="severity-row-label">
          <span class="severity-row-swatch severity-row-swatch-${item.cls}" aria-hidden="true"></span>
          <span class="crash-row-label">${escapeHtml(item.label)}</span>
        </div>
        <strong class="severity-row-count">${fmt(count)}</strong>
        <span class="severity-row-pct">${fmt(share, 0)}%</span>
      </button>
    `;
  }).join("");
}

function buildSeverityLegend(area, animate = false) {
  const hasActiveSeverity = activeSeverityKeys().length > 0;
  return `
    <div class="severity-legend-stack" aria-label="Crash severity counts">
      <div class="network-panel-kicker">Injury</div>
      <div class="severity-legend-rows ${hasActiveSeverity ? "has-active" : ""}">
        ${buildSeverityRows(area, animate)}
      </div>
    </div>
  `;
}

function buildCrashTooltip(crash) {
  const street = titleCase(crash?.street || "Street unavailable");
  const cause = titleCase(crash?.cause || "Unknown");
  const severity = titleCase(crash?.severity || "Unknown");
  const date = String(crash?.date || "").trim();

  return `
    <div class="network-crash-tooltip-grid" style="gap: 2px;">
      <div class="network-crash-tooltip-street" style="font-weight: 800; font-size: 11px;">${escapeHtml(street)}</div>
      <div class="network-crash-tooltip-date" style="font-size: 10px; opacity: 0.8;">${escapeHtml(date)}</div>
      <div class="network-crash-tooltip-cause" style="font-size: 10px; margin-top: 4px; color: #fff;">${escapeHtml(cause)}</div>
      <div class="network-crash-tooltip-severity" style="font-size: 10px; color: #f2c94c;">${escapeHtml(severity)}</div>
    </div>
  `;
}

function wireNetworkPlotHover(scope = panelContent) {
  if (!scope) return;
  const plotFrame = scope.querySelector(".network-plot-frame");
  if (!plotFrame) return;

  const tooltip = plotFrame.querySelector(".network-crash-tooltip");
  const hotspots = plotFrame.querySelectorAll(".network-crash-hotspot");
  if (!tooltip || !hotspots.length) return;

  const hideTooltip = () => {
    tooltip.classList.remove("is-visible");
    tooltip.innerHTML = "";
  };

  hotspots.forEach((hotspot) => {
    const showTooltip = () => {
      const xPct = Number(hotspot.dataset.xpct || 0);
      const yPct = Number(hotspot.dataset.ypct || 0);
      const side = xPct > 0.64 ? "left" : "right";
      const orientation = yPct < 0.22 ? "below" : "above";

      tooltip.dataset.side = side;
      tooltip.dataset.orientation = orientation;
      tooltip.style.left = `${(xPct * 100).toFixed(4)}%`;
      tooltip.style.top = orientation === "below"
        ? `${Math.min(96, yPct * 100 + 6).toFixed(4)}%`
        : `${(yPct * 100).toFixed(4)}%`;
      tooltip.innerHTML = buildCrashTooltip({
        date: hotspot.dataset.date,
        cause: hotspot.dataset.cause,
        severity: hotspot.dataset.severity,
        street: hotspot.dataset.street,
      });
      tooltip.classList.add("is-visible");
    };

    hotspot.addEventListener("mouseenter", showTooltip);
    hotspot.addEventListener("focus", showTooltip);
    hotspot.addEventListener("mouseleave", hideTooltip);
    hotspot.addEventListener("blur", hideTooltip);
    hotspot.addEventListener("click", (event) => {
      event.preventDefault();
      showTooltip();
    });
  });
}

function buildInjuryChart(area, compact = false) {
  const items = injuryBreakdown(area);
  const total = items.reduce((sum, item) => sum + item.value, 0) || 1;
  const severeShare = fmt(severeInjuryShare(area) * 100, 1);
  const rows = items.map((item, index) => {
    const pct = (item.value / total) * 100;
    const width = Math.max(1.5, pct);
    return `
      <div class="injury-bar-row" style="--injury-delay:${index * 56}ms; --share:${width}%;">
        <div class="injury-bar-label">
          <span class="injury-bar-name">${escapeHtml(item.label)}</span>
        </div>
        <strong class="injury-bar-value">${fmt(item.value)}</strong>
        <span class="injury-bar-pct">${fmt(pct, 0)}%</span>
      </div>
    `;
  }).join("");

  return `
    <div class="injury-chart">
      <div class="injury-chart-summary">
        <div class="injury-chart-metric">
          <span>Severe share</span>
          <strong>${severeShare}%</strong>
        </div>
        <div class="injury-chart-metric">
          <span>Total crashes</span>
          <strong>${fmt(area.totalCrashes)}</strong>
        </div>
      </div>
      <div class="injury-bar-list" role="img" aria-label="Crash injury outcomes ordered by severity">
        ${rows}
      </div>
    </div>
  `;
}

function buildCauseChart(area, compact = false, animate = false) {
  const items = causeBreakdown(area);
  const max = Math.max(...items.map((item) => item.count), 1);
  const activeCause = state.crashFilters?.cause || null;

  return `
    <div class="cause-chart ${compact ? "cause-chart-compact" : ""} ${activeCause ? "has-active" : ""}" aria-label="Crash causes">
      <div class="network-panel-kicker" style="margin-top: 14px;">Top causes</div>
      ${items.map((item, index) => {
    const width = (item.count / max) * 100;
    const isActive = activeCause === item.key;
    return `
          <button
            type="button"
            class="crash-row cause-chart-row ${animate ? "is-animated" : ""} ${isActive ? "is-active" : ""}"
            data-crash-cause="${escapeHtml(item.key)}"
            style="--cause-delay: ${index * 60}ms; --share: ${width}%"
            aria-pressed="${isActive ? "true" : "false"}"
          >
            <div class="cause-chart-label">${escapeHtml(item.label)}</div>
            <div class="cause-chart-count">${fmt(item.count)}</div>
          </button>
        `;
  }).join("")}
    </div>
  `;
}

function buildNetworkPlot(area, compact = false) {
  const networkPlot = state.data?.networkPlots?.[area?.name];
  const rawSvgMarkup = typeof networkPlot === "string" ? networkPlot : networkPlot?.svg;
  const svgMarkup = addLaneCasings(rawSvgMarkup);
  const crashMarkers = typeof networkPlot === "object" && networkPlot?.crashMarkers
    ? networkPlot.crashMarkers
    : [];
  const activeSeverities = activeSeverityKeys();
  const activeCause = state.crashFilters?.cause || null;

  if (!svgMarkup) {
    return buildNetworkChart(area, compact);
  }

  const crashHotspots = crashMarkers.length
    ? `
      <div class="network-crash-layer">
        ${crashMarkers.map((crash) => {
      const date = String(crash?.date || "").trim();
      const cause = titleCase(crash?.cause || "Unknown");
      const severity = titleCase(crash?.severity || "Unknown");
      const street = titleCase(crash?.street || "Street unavailable");
      const severityClass = severityKey(crash?.severityKey || crash?.severity);
      const causeKey = normalizeFilterValue(crash?.cause);

      let displayStyle = "";
      let classes = `network-crash-hotspot network-crash-hotspot-${severityClass}`;

      if (!activeSeverities.includes(severityClass)) {
        displayStyle = "display: none;";
      } else if (activeCause) {
        if (causeKey === activeCause) {
          classes += " is-highlighted";
        }
      }

      const label = `${street}. ${date}. ${cause}. ${severity}.`;
      const left = (Number(crash?.xPct || 0) * 100).toFixed(4);
      const top = (Number(crash?.yPct || 0) * 100).toFixed(4);

      return `
            <button
              type="button"
              class="${classes}"
              style="left:${left}%; top:${top}%; ${displayStyle}"
              data-date="${escapeHtml(date)}"
              data-cause="${escapeHtml(cause)}"
              data-cause-key="${escapeHtml(causeKey)}"
              data-severity="${escapeHtml(severity)}"
              data-severity-key="${escapeHtml(severityClass)}"
              data-street="${escapeHtml(street)}"
              data-xpct="${escapeHtml(String(crash?.xPct || 0))}"
              data-ypct="${escapeHtml(String(crash?.yPct || 0))}"
              aria-label="${escapeHtml(label)}"
            ></button>
          `;
    }).join("")}
      </div>
      <div class="network-crash-tooltip" aria-hidden="true"></div>
    `
    : "";

  return `
    <div class="network-plot ${compact ? "network-plot-compact" : ""}">
      <div class="network-plot-frame">
        ${svgMarkup}
        ${crashHotspots}
      </div>
    </div>
  `;
}

function addLaneCasings(svgMarkup) {
  if (typeof svgMarkup !== "string" || !svgMarkup.includes("network-lane-layer")) {
    return svgMarkup;
  }

  return svgMarkup.replace(/<g class="([^"]*\bnetwork-lane-layer\b[^"]*)"([^>]*)>([\s\S]*?)<\/g>/g, (match, className, attrs, body) => {
    const casing = `<g class="${className} network-lane-casing"${attrs}>${body}</g>`;
    return `${casing}${match}`;
  });
}

function buildNetworkChart(area, compact = false, animate = false) {
  const total = Number(area?.laneTotal || 0);
  if (!total) {
    return `
      <div class="network-chart lane-chart ${compact ? "network-chart-compact" : ""}">
        <div class="network-chart-empty">No Bike Lanes</div>
      </div>
    `;
  }

  const rows = laneTypes
    .map(([label, cls], index) => {
      const miles = laneMiles(area, label);
      const share = laneShare(area, label);
      return `
        <div class="network-chart-row ${animate ? "is-animated" : ""}" style="--network-delay:${index * 60}ms; --share:${share}%;">
          <span class="network-chart-label">
            <span class="lane-line lane-line-${cls}"></span>
            <span>${label}</span>
          </span>
          <strong class="network-chart-value">${fmt(miles, 1)} mi</strong>
          <span class="network-chart-pct">${fmt(share, 0)}%</span>
        </div>
      `;
    })
    .join("");

  return `
    <div class="network-chart lane-chart ${compact ? "network-chart-compact" : ""}">
      <div class="network-chart-rows">${rows}</div>
    </div>
  `;
}

function sx(x) {
  return PLOT.originX + x * PLOT.cell;
}

function sy(y) {
  return PLOT.originY + y * PLOT.cell;
}

function layoutFor(area, index) {
  return {
    x: sx(area.gridX) - PLOT.tile / 2,
    y: sy(area.gridY) - PLOT.tile / 2,
    size: PLOT.tile,
  };
}

function drawCityOutline() {
  const rings = state.data.cityOutline || [];
  lakeLayer.innerHTML = rings
    .map((ring) => {
      const d = ring
        .map(([x, y], index) => `${index ? "L" : "M"} ${sx(x).toFixed(1)} ${sy(y).toFixed(1)}`)
        .join(" ");
      return `<path class="city-outline" d="${d} Z"></path>`;
    })
    .join("");
}

function renderTiles() {
  tileLayer.innerHTML = "";
  state.areas.forEach((area, index) => {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.classList.add("tile-group");
    group.dataset.name = area.name;
    group.innerHTML = `
      <rect class="tile" />
      <g class="risk-meter">
        <path class="risk-unit" d="M 5 0 C 5 0, 0 8, 0 11 A 5 5 0 1 0 10 11 C 10 8, 5 0, 5 0 Z" />
        <path class="risk-unit" d="M 5 0 C 5 0, 0 8, 0 11 A 5 5 0 1 0 10 11 C 10 8, 5 0, 5 0 Z" />
        <path class="risk-unit" d="M 5 0 C 5 0, 0 8, 0 11 A 5 5 0 1 0 10 11 C 10 8, 5 0, 5 0 Z" />
        <path class="risk-unit" d="M 5 0 C 5 0, 0 8, 0 11 A 5 5 0 1 0 10 11 C 10 8, 5 0, 5 0 Z" />
        <path class="risk-unit" d="M 5 0 C 5 0, 0 8, 0 11 A 5 5 0 1 0 10 11 C 10 8, 5 0, 5 0 Z" />
      </g>
      <rect class="badge" />
      <text class="tile-label"></text>
      <text class="tile-stars"></text>
    `;
    group.addEventListener("mouseenter", () => {
      if (!state.hoverEnabled) return;
      setHoveredArea(area.name);
    });
    group.addEventListener("mouseleave", () => {
      if (!state.hoverEnabled) return;
      setHoveredArea(null);
    });
    group.addEventListener("click", () => selectArea(area.name));
    group.style.setProperty("--delay", `${index * 24}ms`);
    tileLayer.append(group);
    updateTile(group, area, index);
  });
}

function updateTile(group, area, index) {
  const { x, y, size } = layoutFor(area, index);
  const badgeHeight = size * 0.25;
  const badgeY = size * 0.0525;
  group.style.setProperty("--tile-x", `${x}px`);
  group.style.setProperty("--tile-y", `${y}px`);
  group.classList.toggle("selected", Boolean(state.selected && state.selected.name === area.name));
  group.classList.toggle("hovered", Boolean(state.hovered && state.hovered === area.name));

  const tile = group.querySelector(".tile");
  tile.setAttribute("width", size);
  tile.setAttribute("height", size);
  tile.setAttribute("fill", colorFor(area));

  const riskMeter = group.querySelector(".risk-meter");
  const units = riskMeter.querySelectorAll(".risk-unit");
  const dropScale = (size / 75) * 0.6; // 40% smaller than the original tile drops
  const dropCenterOffset = 5 * dropScale;
  const dropSpread = size * 0.56;
  const gap = dropSpread / 4;
  const startX = (size - dropSpread) / 2;
  const meterY = size - (16 * dropScale) - (size * 0.05);
  const filledUnits = injuryDropCount(area);

  units.forEach((unit, i) => {
    unit.setAttribute("transform", `translate(${startX + i * gap - dropCenterOffset}, ${meterY}) scale(${dropScale})`);
    unit.setAttribute("fill", i < filledUnits ? "var(--red)" : "transparent");
    unit.style.opacity = i < filledUnits ? "0.5" : "0";
  });

  const badge = group.querySelector(".badge");
  badge.setAttribute("width", size * 1.1);
  badge.setAttribute("height", badgeHeight);
  badge.setAttribute("x", -size * 0.05);
  badge.setAttribute("y", badgeY);
  badge.setAttribute("fill", "rgba(0, 0, 0, 0.4)");
  badge.setAttribute("stroke", "none");

  const label = group.querySelector(".tile-label");
  label.textContent = area.abbrev;
  label.setAttribute("x", size / 2);
  label.setAttribute("y", badgeY + badgeHeight / 2 + 2.4);
  label.style.fontSize = "8.5px";
  label.removeAttribute("textLength");
  label.removeAttribute("lengthAdjust");

  const stars = group.querySelector(".tile-stars");
  stars.textContent = starString(area.bikeRank);
  stars.setAttribute("x", size / 2);
  stars.setAttribute("y", size / 2 + 3.2);
  stars.style.fontSize = "10px";
}

function updateMap() {
  drawCityOutline();
  [...tileLayer.children].forEach((group, index) => {
    const area = state.areas[index];
    updateTile(group, area, index);
  });
}

function syncTileState() {
  [...tileLayer.children].forEach((group, index) => {
    const area = state.areas[index];
    group.classList.toggle("selected", Boolean(state.selected && state.selected.name === area.name));
    group.classList.toggle("hovered", Boolean(state.hovered && state.hovered === area.name));
  });
}

function setHoveredArea(name) {
  state.hovered = name ? state.areas.find((area) => area.name === name) : null;
  syncTileState();
}

function renderHoverSpotlight(area) {
  if (!hoverSpotlight) return;
  hoverSpotlight.innerHTML = "";
  hoverSpotlight.classList.remove("is-visible");
}

function selectArea(name) {
  if (!name || name.trim() === "") {
    renderDefaultPanel();
    return;
  }
  const area = state.areas.find((item) => item.name.toLowerCase() === name.toLowerCase());
  if (!area) return;
  state.selected = area;
  state.hovered = area;
  state.crashFilters = {
    severities: [...DEFAULT_SEVERITY_FILTERS],
    cause: null,
  };
  renderActivePanels(area, { animate: true });
  search.value = area.name;
  syncTileState();

  if (!state.firstSelectionDone) {
    state.firstSelectionDone = true;
    hideInitialTip();
    state.hoverEnabled = false;
    document.body.classList.remove("hover-ready");
    if (state.hoverTimer) window.clearTimeout(state.hoverTimer);
    state.hoverTimer = window.setTimeout(() => {
      state.hoverEnabled = true;
      document.body.classList.add("hover-ready");
      if (state.hovered) {
        renderHoverSpotlight(state.areas.find((area) => area.name === state.hovered));
      }
      state.hoverTimer = null;
    }, FLIP_MS);
  }
}

function renderRightOverviewPanel(area, { animate = false } = {}) {
  panelContent.innerHTML = `
    <div class="context-panel ${animate ? "is-flipping" : ""}">
      <div class="context-mini-stats">
        <div class="context-mini-stat"><span>Population</span><strong>${fmt(area.population)}</strong></div>
        <div class="context-mini-stat"><span>Bikeability</span><strong>${starString(area.bikeRank)}</strong></div>
      </div>
    </div>
  `;
  if (animate) {
    panelContent.classList.remove("is-flipped");
    requestAnimationFrame(() => panelContent.classList.add("is-flipping"));
    window.setTimeout(() => panelContent.classList.remove("is-flipping"), FLIP_MS);
  } else {
    panelContent.classList.remove("is-flipping");
  }
}

function renderNetworkPanel(area, { animate = false } = {}) {
  if (!networkPanelContent) return;

  if (!area) {
    networkPanelContent.innerHTML = `
      <div class="network-panel-shell">
        <div class="network-panel-kicker">Bike network</div>
        <div class="network-panel-empty">Select a community.</div>
      </div>
    `;
    networkPanelContent.classList.remove("is-flipping");
    return;
  }

  networkPanelContent.innerHTML = `
    <div class="network-panel-shell ${animate ? "is-flipping" : ""}">
      <div class="network-panel-header">
        <div class="network-panel-title">
          ${escapeHtml(area.name)}
          ${buildBikeabilityHelpButton()}
        </div>
      </div>
      <section class="context-chart-card context-network-card">
        <div class="network-panel-region network-panel-region-crashes">
          <div class="context-mini-stat" style="margin-bottom: 12px;">
            <span>Crashes</span>
            <strong>${fmt(area.totalCrashes)}</strong>
          </div>
          <div class="network-crash-legend-grid">
            ${buildCauseChart(area, true, animate)}
          </div>
        </div>
        <div class="network-panel-region network-panel-region-lanes">
          <div class="lane-plot">
            ${buildSeverityLegend(area, animate)}
          </div>
        </div>
      </section>
    </div>
  `;

  if (animate) {
    networkPanelContent.classList.remove("is-flipped");
    requestAnimationFrame(() => networkPanelContent.classList.add("is-flipping"));
    window.setTimeout(() => networkPanelContent.classList.remove("is-flipping"), FLIP_MS);
  } else {
    networkPanelContent.classList.remove("is-flipping");
  }
}

function renderNetworkMapDock(area, { animate = false } = {}) {
  if (!networkMapDockContent) return;

  if (!area) {
    networkMapDockContent.innerHTML = "";
    networkMapDockContent.parentElement?.classList.remove("is-visible");
    return;
  }

  networkMapDockContent.parentElement?.classList.add("is-visible");
  networkMapDockContent.innerHTML = `
    <div class="network-map-dock-shell ${animate ? "is-flipping" : ""}">
      ${buildNetworkPlot(area, false)}
      <div class="network-map-dock-severity">
        <div class="network-panel-kicker">Bike network</div>
        ${buildNetworkChart(area, true, animate)}
      </div>
    </div>
  `;
  wireNetworkPlotHover(networkMapDockContent);
}

function renderActivePanels(area, { animate = false } = {}) {
  if (!area) {
    renderDefaultPanel();
    renderNetworkPanel(null);
    renderNetworkMapDock(null);
    renderHoverSpotlight(null);
    return;
  }

  renderHoverSpotlight(area);
  renderRightOverviewPanel(area, { animate });
  renderNetworkPanel(area, { animate });
  renderNetworkMapDock(area, { animate });
}

function renderDefaultPanel() {
  const citywide = state.data?.citywide || {};
  const citywideBikeCrashes = Number(citywide.bikeCrashes ?? citywide.crashes ?? 1) || 1;
  state.selected = null;
  state.hovered = null;
  state.crashFilters = {
    severities: [...DEFAULT_SEVERITY_FILTERS],
    cause: null,
  };
  search.value = "";
  panelContent.innerHTML = `
    <div class="context-panel context-panel-default">
      <div style="margin-top: 24px; padding: 0 4px;">
        ${buildBikeabilityLegend()}
      </div>
    </div>
  `;

  if (networkPanelContent) {
    networkPanelContent.innerHTML = `
      <div class="network-panel-shell">
        <div class="network-panel-header">
          <div class="network-panel-title">
            Chicago Bikeability Map
            ${buildBikeabilityHelpButton()}
          </div>
        </div>
        <section class="context-chart-card context-network-card">
          <div class="network-panel-region network-panel-region-crashes">
            <div class="context-mini-stats" style="margin-bottom: 12px;">
              <div class="context-mini-stat">
                <span>Population</span>
                <strong>${fmt(citywide.population || 0)}</strong>
              </div>
              <div class="context-mini-stat">
                <span>Crashes</span>
                <strong>${fmt(citywideBikeCrashes)}</strong>
              </div>
            </div>
            <div class="network-crash-legend-grid">
              ${buildCauseChart(citywide, true, false)}
            </div>
          </div>
          <div class="network-panel-region network-panel-region-lanes">
            <div class="lane-plot">
              ${buildSeverityLegend(citywide, false)}
            </div>
          </div>
        </section>
      </div>
    `;
    networkPanelContent.classList.remove("is-flipping");
  }

  syncTileState();
  renderNetworkMapDock(null);
  renderHoverSpotlight(null);

  showInitialTip();
}

function loadEmbeddedData() {
  const node = document.querySelector("#atlas-data");
  if (!node) return null;

  const raw = node.textContent?.trim();
  if (!raw) return null;

  try {
    return JSON.parse(raw);
  } catch (error) {
    console.warn("Unable to parse embedded atlas data", error);
    return null;
  }
}

async function init() {
  state.data = loadEmbeddedData();
  if (!state.data) {
    const response = await fetch("data/atlas-data.json?v=2", { cache: "no-store" });
    state.data = await response.json();
  }

  state.areas = state.data.areas;
  datalist.innerHTML = state.areas.map((area) => `<option value="${area.name}"></option>`).join("");
  renderTiles();
  renderDefaultPanel();
  updateMap();
  requestAnimationFrame(() => {
    document.body.classList.add("is-loaded");
    setTimeout(() => {
      document.body.classList.add("hover-ready");
      document.querySelectorAll(".tile-group").forEach(group => {
        group.style.removeProperty("--delay");
      });
    }, 1200);
  });

  if (networkPanelContent) {
    networkPanelContent.addEventListener("click", (event) => {
      const severityButton = event.target.closest("[data-crash-severity]");
      if (severityButton) {
        event.preventDefault();
        setCrashFilter("severity", severityButton.dataset.crashSeverity);
        return;
      }

      const causeButton = event.target.closest("[data-crash-cause]");
      if (causeButton) {
        event.preventDefault();
        setCrashFilter("cause", causeButton.dataset.crashCause);
      }
    });
  }

  const customCursor = document.getElementById("custom-cursor");
  if (customCursor) {
    const customCursorImg = customCursor.querySelector("img");
    let cursorRotation = 0;

    // Throttle glitter generation slightly
    let lastGlitterTime = 0;
    let lastMouseX = 0;
    let lastMouseY = 0;

    document.addEventListener("mousemove", (e) => {
      customCursor.style.left = e.clientX + "px";
      customCursor.style.top = e.clientY + "px";

      const deltaX = e.clientX - (lastMouseX || e.clientX);
      const deltaY = e.clientY - (lastMouseY || e.clientY);
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;

      const speed = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

      const now = performance.now();
      if (now - lastGlitterTime > (speed > 10 ? 12 : 32)) {
        lastGlitterTime = now;

        if (speed > 0.5) {
          const dirX = deltaX / speed;
          const dirY = deltaY / speed;
          const normX = -dirY;
          const normY = dirX;

          // Width of the wheel trail (half width)
          const trailWidth = 5;
          const wheelOffsetY = 0;

          const pLeft = document.createElement("div");
          pLeft.className = "glitter-particle";
          pLeft.style.left = (e.clientX + normX * trailWidth) + "px";
          pLeft.style.top = (e.clientY + wheelOffsetY + normY * trailWidth) + "px";

          const pRight = document.createElement("div");
          pRight.className = "glitter-particle";
          pRight.style.left = (e.clientX - normX * trailWidth) + "px";
          pRight.style.top = (e.clientY + wheelOffsetY - normY * trailWidth) + "px";

          const size = Math.random() * 2 + 1;
          pLeft.style.width = size + "px"; pLeft.style.height = size + "px";
          pRight.style.width = size + "px"; pRight.style.height = size + "px";

          document.body.appendChild(pLeft);
          document.body.appendChild(pRight);

          const animOptions = { duration: 400 + Math.random() * 200, easing: 'ease-out' };

          pLeft.animate([
            { opacity: 1, transform: 'translate(-50%, -50%) scale(1)' },
            { opacity: 0, transform: 'translate(-50%, -50%) scale(0.1)' }
          ], animOptions).onfinish = () => pLeft.remove();

          pRight.animate([
            { opacity: 1, transform: 'translate(-50%, -50%) scale(1)' },
            { opacity: 0, transform: 'translate(-50%, -50%) scale(0.1)' }
          ], animOptions).onfinish = () => pRight.remove();
        }
      }
    });

    document.addEventListener("mousedown", () => {
      cursorRotation += 1080;
      if (customCursorImg) {
        customCursorImg.style.transition = "transform 1s cubic-bezier(0.2, 0.95, 0.3, 1)";
        customCursorImg.style.transform = `rotate(${cursorRotation}deg)`;
      }
    });
  }

  search.addEventListener("change", () => selectArea(search.value));
  search.addEventListener("input", () => {
    const exact = state.areas.find((area) => area.name.toLowerCase() === search.value.toLowerCase());
    if (exact) selectArea(exact.name);
  });
}

function setCrashFilter(kind, value) {
  const normalizedValue = normalizeFilterValue(value);

  if (kind === "severity") {
    const current = activeSeverityKeys();
    const next = current.includes(normalizedValue)
      ? current.filter((item) => item !== normalizedValue)
      : [...current, normalizedValue];
    state.crashFilters = {
      severities: next,
      cause: state.crashFilters?.cause || null,
    };
  } else if (state.crashFilters?.cause === normalizedValue) {
    state.crashFilters = {
      severities: activeSeverityKeys(),
      cause: null,
    };
  } else {
    state.crashFilters = {
      severities: activeSeverityKeys(),
      cause: normalizedValue,
    };
  }

  updateNetworkFilters();
}

function updateNetworkFilters() {
  const activeSeverities = activeSeverityKeys();
  const activeCause = state.crashFilters?.cause || null;

  document.querySelectorAll(".cause-chart").forEach(chart => {
    chart.classList.toggle("has-active", Boolean(activeCause));
  });

  const causeRows = document.querySelectorAll(".cause-chart-row");
  causeRows.forEach(row => {
    const rowCause = normalizeFilterValue(row.dataset.crashCause);
    const isActive = activeCause === rowCause;
    row.classList.toggle("is-active", isActive);
    row.setAttribute("aria-pressed", isActive ? "true" : "false");
  });

  document.querySelectorAll(".severity-legend-rows").forEach(chart => {
    chart.classList.toggle("has-active", activeSeverities.length > 0);
  });

  const severityRows = document.querySelectorAll(".severity-row");
  severityRows.forEach(row => {
    const rowSeverity = normalizeFilterValue(row.dataset.crashSeverity);
    const isActive = activeSeverities.includes(rowSeverity);
    row.classList.toggle("is-active", isActive);
    row.setAttribute("aria-pressed", isActive ? "true" : "false");
  });

  const hotspots = document.querySelectorAll(".network-crash-hotspot");
  hotspots.forEach(hotspot => {
    const crashSeverity = severityKey(hotspot.dataset.severityKey || hotspot.dataset.severity);
    const crashCause = normalizeFilterValue(hotspot.dataset.causeKey || hotspot.dataset.cause);

    if (!activeSeverities.includes(crashSeverity)) {
      hotspot.style.display = "none";
      hotspot.classList.remove("is-highlighted", "is-muted");
      return;
    }

    hotspot.style.display = "";

    if (activeCause) {
      if (crashCause === activeCause) {
        hotspot.classList.add("is-highlighted");
        hotspot.classList.remove("is-muted");
      } else {
        hotspot.classList.remove("is-highlighted", "is-muted");
      }
    } else {
      hotspot.classList.remove("is-highlighted", "is-muted");
    }
  });
}

init();
