/* India Job-Loss Tracker — dashboard logic.
 * Loads the JSON store, applies filters, and renders KPIs, charts, a map,
 * and a table. No build step; runs as a static page.
 */
(() => {
  "use strict";

  const DATA_URL = "./data/layoffs.json";
  const SAMPLE_URL = "./data/sample.json";

  const PALETTE = [
    "#6366f1", "#2dd4bf", "#f59e0b", "#f87171", "#a78bfa", "#34d399",
    "#60a5fa", "#fb923c", "#f472b6", "#facc15", "#4ade80", "#38bdf8",
    "#c084fc", "#fbbf24", "#fb7185", "#22d3ee", "#818cf8", "#a3e635",
    "#e879f9", "#94a3b8",
  ];
  const TEXT = "#e6edf3";
  const MUTED = "#8aa0b3";
  const GRID = "rgba(255,255,255,0.06)";

  const state = {
    records: [],
    metric: "headcount", // or "events"
    charts: {},
    map: null,
    markerLayer: null,
    usingSample: false,
  };

  // --- helpers -------------------------------------------------------------
  const $ = (sel) => document.querySelector(sel);
  const fmt = (n) => (n == null ? "—" : n.toLocaleString("en-IN"));

  function measure(record) {
    return state.metric === "events" ? 1 : record.headcount || 0;
  }

  function aggregate(records, keyFn) {
    const map = new Map();
    for (const r of records) {
      const key = keyFn(r);
      if (key == null || key === "") continue;
      map.set(key, (map.get(key) || 0) + measure(r));
    }
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }

  // --- filtering -----------------------------------------------------------
  function currentFilters() {
    return {
      sector: $("#f-sector").value,
      region: $("#f-region").value,
      from: $("#f-from").value, // YYYY-MM
      to: $("#f-to").value,
      ai: $("#f-ai").checked,
      search: $("#f-search").value.trim().toLowerCase(),
    };
  }

  function applyFilters() {
    const f = currentFilters();
    return state.records.filter((r) => {
      if (f.sector && r.sector !== f.sector) return false;
      if (f.region && r.region !== f.region) return false;
      if (f.ai && !r.ai_related) return false;
      if (f.from && (r.month || "") < f.from) return false;
      if (f.to && (r.month || "") > f.to) return false;
      if (f.search) {
        const hay = `${r.company} ${r.city || ""} ${r.state || ""} ${r.sector} ${r.summary || ""}`.toLowerCase();
        if (!hay.includes(f.search)) return false;
      }
      return true;
    });
  }

  // --- rendering -----------------------------------------------------------
  function renderKpis(records) {
    const events = records.length;
    const headcount = records.reduce((s, r) => s + (r.headcount || 0), 0);
    const companies = new Set(records.map((r) => r.company.toLowerCase())).size;
    const ai = records.filter((r) => r.ai_related);
    const aiHead = ai.reduce((s, r) => s + (r.headcount || 0), 0);

    const cards = [
      { value: fmt(events), label: "Layoff events" },
      { value: fmt(headcount), label: "People laid off (reported)" },
      { value: fmt(companies), label: "Companies" },
      { value: fmt(ai.length), label: "AI-related events", ai: true },
      { value: fmt(aiHead), label: "AI-related layoffs", ai: true },
    ];
    $("#kpis").innerHTML = cards
      .map(
        (c) =>
          `<div class="kpi ${c.ai ? "ai" : ""}"><div class="value">${c.value}</div><div class="label">${c.label}</div></div>`
      )
      .join("");
  }

  function baseOptions(extra = {}) {
    return Object.assign(
      {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: MUTED, boxWidth: 12 } },
        },
      },
      extra
    );
  }

  function destroyChart(id) {
    if (state.charts[id]) {
      state.charts[id].destroy();
      delete state.charts[id];
    }
  }

  function metricLabel() {
    return state.metric === "events" ? "Layoff events" : "Headcount";
  }

  function renderTimeChart(records) {
    destroyChart("time");
    const byMonth = new Map();
    for (const r of records) {
      const m = r.month;
      if (!m) continue;
      if (!byMonth.has(m)) byMonth.set(m, { head: 0, events: 0 });
      const e = byMonth.get(m);
      e.head += r.headcount || 0;
      e.events += 1;
    }
    const months = [...byMonth.keys()].sort();
    const head = months.map((m) => byMonth.get(m).head);
    const events = months.map((m) => byMonth.get(m).events);

    const ctx = $("#chart-time");
    state.charts.time = new Chart(ctx, {
      data: {
        labels: months,
        datasets: [
          {
            type: "bar",
            label: "Headcount",
            data: head,
            backgroundColor: "rgba(99,102,241,0.55)",
            borderColor: "#6366f1",
            yAxisID: "y",
            order: 2,
          },
          {
            type: "line",
            label: "Events",
            data: events,
            borderColor: "#2dd4bf",
            backgroundColor: "#2dd4bf",
            tension: 0.25,
            yAxisID: "y1",
            order: 1,
          },
        ],
      },
      options: baseOptions({
        scales: {
          x: { ticks: { color: MUTED, maxRotation: 0, autoSkip: true }, grid: { color: GRID } },
          y: { position: "left", ticks: { color: MUTED }, grid: { color: GRID }, title: { display: true, text: "Headcount", color: MUTED } },
          y1: { position: "right", ticks: { color: MUTED }, grid: { drawOnChartArea: false }, title: { display: true, text: "Events", color: MUTED } },
        },
      }),
    });
  }

  function barChart(id, canvasSel, records, keyFn, { horizontal = true, top = null } = {}) {
    destroyChart(id);
    let data = aggregate(records, keyFn);
    if (top) data = data.slice(0, top);
    const labels = data.map((d) => d[0]);
    const values = data.map((d) => d[1]);
    state.charts[id] = new Chart($(canvasSel), {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: metricLabel(),
            data: values,
            backgroundColor: labels.map((_, i) => PALETTE[i % PALETTE.length]),
            borderRadius: 4,
          },
        ],
      },
      options: baseOptions({
        indexAxis: horizontal ? "y" : "x",
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: MUTED }, grid: { color: GRID } },
          y: { ticks: { color: MUTED }, grid: { color: GRID } },
        },
      }),
    });
  }

  function doughnutChart(id, canvasSel, records, keyFn) {
    destroyChart(id);
    const data = aggregate(records, keyFn);
    state.charts[id] = new Chart($(canvasSel), {
      type: "doughnut",
      data: {
        labels: data.map((d) => d[0]),
        datasets: [
          {
            data: data.map((d) => d[1]),
            backgroundColor: data.map((_, i) => PALETTE[i % PALETTE.length]),
            borderColor: "#161f2b",
            borderWidth: 2,
          },
        ],
      },
      options: baseOptions({ cutout: "58%" }),
    });
  }

  function renderMap(records) {
    if (!state.map) {
      state.map = L.map("map", { scrollWheelZoom: false }).setView([22.5, 79], 4);
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        maxZoom: 18,
      }).addTo(state.map);
      state.markerLayer = L.layerGroup().addTo(state.map);
    }
    state.markerLayer.clearLayers();

    // Aggregate by city (records sharing coords collapse into one bubble).
    const cities = new Map();
    for (const r of records) {
      if (r.lat == null || r.lng == null) continue;
      const key = `${r.city}|${r.lat}|${r.lng}`;
      if (!cities.has(key)) {
        cities.set(key, { city: r.city, lat: r.lat, lng: r.lng, value: 0, events: 0, companies: new Set() });
      }
      const c = cities.get(key);
      c.value += measure(r);
      c.events += 1;
      c.companies.add(r.company);
    }

    const values = [...cities.values()].map((c) => c.value);
    const maxV = Math.max(1, ...values);
    for (const c of cities.values()) {
      const radius = 8 + 26 * Math.sqrt(c.value / maxV);
      L.circleMarker([c.lat, c.lng], {
        radius,
        color: "#f59e0b",
        fillColor: "#f59e0b",
        fillOpacity: 0.35,
        weight: 1.5,
      })
        .bindPopup(
          `<strong>${c.city}</strong><br>${metricLabel()}: ${fmt(c.value)}<br>` +
            `Events: ${c.events}<br>Companies: ${c.companies.size}`
        )
        .addTo(state.markerLayer);
    }
  }

  function renderTable(records) {
    const tbody = $("#records tbody");
    $("#record-count").textContent = `(${records.length})`;
    if (!records.length) {
      tbody.innerHTML = `<tr class="records-empty"><td colspan="7">No records match the current filters.</td></tr>`;
      return;
    }
    const rows = records.slice(0, 300).map((r) => {
      const loc = [r.city, r.state].filter(Boolean).join(", ") || (r.region !== "Unknown" ? r.region : "—");
      const src = r.source_url && r.source_url !== "#"
        ? `<a href="${r.source_url}" target="_blank" rel="noopener">${r.source_name || "link"}</a>`
        : (r.source_name || "—");
      const ai = r.ai_related ? `<span class="tag-ai" title="${(r.ai_rationale || "AI-related")}">AI</span>` : "";
      return `<tr>
        <td>${r.date || r.month || "—"}</td>
        <td>${r.company}</td>
        <td>${r.sector}</td>
        <td>${loc}</td>
        <td class="num">${fmt(r.headcount)}</td>
        <td>${ai}</td>
        <td>${src}</td>
      </tr>`;
    });
    tbody.innerHTML = rows.join("");
  }

  function renderAll() {
    const records = applyFilters();
    renderKpis(records);
    renderTimeChart(records);
    barChart("sector", "#chart-sector", records, (r) => r.sector, { horizontal: true });
    doughnutChart("region", "#chart-region", records, (r) => r.region);
    barChart("state", "#chart-state", records, (r) => r.state, { horizontal: true, top: 10 });
    renderMap(records);
    renderTable(records);
    if (state.map) setTimeout(() => state.map.invalidateSize(), 50);
  }

  // --- setup ---------------------------------------------------------------
  function populateSelects() {
    const sectors = [...new Set(state.records.map((r) => r.sector))].sort();
    const regions = [...new Set(state.records.map((r) => r.region))].sort();
    $("#f-sector").innerHTML =
      `<option value="">All sectors</option>` +
      sectors.map((s) => `<option value="${s}">${s}</option>`).join("");
    $("#f-region").innerHTML =
      `<option value="">All regions</option>` +
      regions.map((s) => `<option value="${s}">${s}</option>`).join("");
  }

  function setUpdated(meta) {
    const el = $("#updated");
    if (meta && meta.generated_at) {
      const d = new Date(meta.generated_at);
      el.textContent = "Updated " + d.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
    } else {
      el.textContent = "Not yet updated";
    }
  }

  async function loadData(url, isSample) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`Failed to load ${url}: ${res.status}`);
    const data = await res.json();
    state.records = data.records || [];
    state.usingSample = !!isSample;
    setUpdated(data.meta);
    populateSelects();

    $("#empty-banner").classList.toggle("hidden", state.records.length > 0 || isSample);
    $("#sample-banner").classList.toggle("hidden", !isSample);
    renderAll();
  }

  function wireEvents() {
    ["#f-sector", "#f-region", "#f-from", "#f-to", "#f-ai"].forEach((sel) =>
      $(sel).addEventListener("change", renderAll)
    );
    let t;
    $("#f-search").addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(renderAll, 200);
    });
    $("#reset").addEventListener("click", () => {
      ["#f-sector", "#f-region", "#f-from", "#f-to", "#f-search"].forEach((s) => ($(s).value = ""));
      $("#f-ai").checked = false;
      renderAll();
    });
    document.querySelectorAll("#metric-toggle button").forEach((btn) =>
      btn.addEventListener("click", () => {
        document.querySelectorAll("#metric-toggle button").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.metric = btn.dataset.metric;
        renderAll();
      })
    );
    $("#load-sample").addEventListener("click", () => loadData(SAMPLE_URL, true));
    $("#load-live").addEventListener("click", () => loadData(DATA_URL, false));
  }

  // --- boot ----------------------------------------------------------------
  Chart.defaults.color = MUTED;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  wireEvents();
  loadData(DATA_URL, false).catch((err) => {
    console.error(err);
    $("#empty-banner").classList.remove("hidden");
    $("#empty-banner").querySelector("div").innerHTML =
      "<strong>Couldn't load data.</strong> Open the browser console for details, or preview with sample data.";
  });
})();
