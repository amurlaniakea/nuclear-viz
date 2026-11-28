const chartEl = document.getElementById('chart');
const detailEl = document.getElementById('detail');
const selectEl = document.getElementById('chain-select');

const MODE_COLORS = {
  alpha: '#f97316',
  'beta-': '#38bdf8',
  'beta+': '#a78bfa',
  gamma: '#94a3b8',
  stable: '#22c55e'
};

// Modo de datos: lo fija cada index.html con <meta name="nv-mode" content="api|static">.
//   api    -> backend FastAPI (/api/...)        static -> JSON precomputados (GitHub Pages)
const MODE = document.querySelector('meta[name="nv-mode"]')?.content === 'static' ? 'static' : 'api';
const ENDPOINTS = {
  api: {
    chains: () => '/api/chains',
    chain: (id) => `/api/chains/${encodeURIComponent(id)}`,
    note: 'Los datos de esta cadena están simplificados con fines educativos. ' +
      'Los núclidos fuera del dataset local se consultan en /api/nuclide/Símbolo-A (IAEA Livechart, ENSDF).'
  },
  static: {
    chains: () => './data/chains_index.json',
    chain: (id) => `./data/${encodeURIComponent(id)}.json`,
    note: 'Los datos de esta cadena están simplificados con fines educativos. ' +
      'La consulta remota (IAEA Livechart) requiere el servidor backend.'
  }
}[MODE];

const searchForm = document.getElementById('nuclide-search');
const searchInput = document.getElementById('nuclide-query');
const searchResultEl = document.getElementById('search-result');
const levelsPanelEl = document.getElementById('levels-panel');
let levelsSeq = 0;
let searchSeq = 0;

let currentChain = null;
let selectedNuclideId = null;

document.addEventListener('DOMContentLoaded', () => {
  initSearch();
  initExport();
  init();
});

async function init() {
  try {
    const res = await fetch(ENDPOINTS.chains());
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    const chains = payload.chains || [];

    if (!chains.length) {
      detailEl.textContent = 'No hay cadenas disponibles.';
      return;
    }

    selectEl.innerHTML = '';
    for (const chain of chains) {
      const option = document.createElement('option');
      option.value = chain.id;
      option.textContent = chain.name;
      selectEl.appendChild(option);
    }

    selectEl.addEventListener('change', async () => {
      await loadChain(selectEl.value);
    });

    await loadChain(chains[0].id);
  } catch (error) {
    detailEl.textContent = `Error cargando datos: ${error.message}`;
  }
}

async function loadChain(chainId) {
  try {
    const res = await fetch(ENDPOINTS.chain(chainId));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentChain = await res.json();
    selectedNuclideId = currentChain.parent || currentChain.nuclides?.[0]?.id || null;
    renderAll();
  } catch (error) {
    detailEl.textContent = `Error cargando cadena: ${error.message}`;
  }
}

function renderAll() {
  renderChart();
  renderTable();
  renderDetail(selectedNuclideId);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function svgEl(tag, attrs = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) {
    el.setAttribute(key, String(value));
  }
  return el;
}

function scaler(min, max, rangeMin, rangeMax) {
  const span = (max - min) || 1;
  return (value) => rangeMin + ((value - min) / span) * (rangeMax - rangeMin);
}

function makeTicks(min, max, targetCount) {
  const span = max - min;
  if (span <= 0) return [min];

  const step = Math.max(1, Math.round(span / Math.max(1, targetCount)));
  const ticks = [];
  const start = Math.ceil(min / step) * step;

  for (let value = start; value <= max; value += step) {
    ticks.push(value);
  }

  return ticks;
}

function addMarker(defs, id, color) {
  const marker = svgEl('marker', {
    id,
    markerWidth: 10,
    markerHeight: 10,
    refX: 8,
    refY: 4,
    orient: 'auto'
  });

  const path = svgEl('path', {
    d: 'M0,0 L8,4 L0,8 z',
    fill: color
  });

  marker.appendChild(path);
  defs.appendChild(marker);
}

function edgeColor(mode) {
  if (mode === 'alpha') return MODE_COLORS.alpha;
  if (mode === 'beta-') return MODE_COLORS['beta-'];
  if (mode === 'beta+' || mode === 'ec') return MODE_COLORS['beta+'];
  return MODE_COLORS.gamma;
}

function markerForMode(mode) {
  if (mode === 'alpha') return 'url(#arrow-alpha)';
  if (mode === 'beta-') return 'url(#arrow-beta-minus)';
  if (mode === 'beta+' || mode === 'ec') return 'url(#arrow-beta-plus)';
  return '';
}

function renderChart() {
  chartEl.innerHTML = '';
  if (!currentChain) return;

  const width = 1100;
  const height = 760;
  const margin = { top: 30, right: 40, bottom: 78, left: 78 };

  const nuclides = (currentChain.nuclides || []).map((item) => ({
    ...item,
    n: item.a - item.z
  }));

  if (!nuclides.length) {
    chartEl.textContent = 'Sin núclidos para esta cadena.';
    return;
  }

  const byId = Object.fromEntries(nuclides.map((item) => [item.id, item]));

  const minX = Math.min(...nuclides.map((item) => item.n)) - 3;
  const maxX = Math.max(...nuclides.map((item) => item.n)) + 3;
  const minY = Math.min(...nuclides.map((item) => item.z)) - 3;
  const maxY = Math.max(...nuclides.map((item) => item.z)) + 3;

  const xScale = scaler(minX, maxX, margin.left, width - margin.right);
  const yScale = scaler(minY, maxY, height - margin.bottom, margin.top);

  const svg = svgEl('svg', {
    viewBox: `0 0 ${width} ${height}`,
    width: '100%',
    height: '100%'
  });

  const defs = svgEl('defs');
  addMarker(defs, 'arrow-alpha', MODE_COLORS.alpha);
  addMarker(defs, 'arrow-beta-minus', MODE_COLORS['beta-']);
  addMarker(defs, 'arrow-beta-plus', MODE_COLORS['beta+']);
  svg.appendChild(defs);

  const xTicks = makeTicks(minX, maxX, 8);
  const yTicks = makeTicks(minY, maxY, 8);

  for (const tick of xTicks) {
    const x = xScale(tick);

    svg.appendChild(svgEl('line', {
      x1: x,
      y1: margin.top,
      x2: x,
      y2: height - margin.bottom,
      stroke: '#0f172a',
      'stroke-width': 1
    }));

    const text = svgEl('text', {
      x,
      y: height - margin.bottom + 24,
      fill: '#64748b',
      'font-size': 12,
      'text-anchor': 'middle'
    });

    text.textContent = tick;
    svg.appendChild(text);
  }

  for (const tick of yTicks) {
    const y = yScale(tick);

    svg.appendChild(svgEl('line', {
      x1: margin.left,
      y1: y,
      x2: width - margin.right,
      y2: y,
      stroke: '#0f172a',
      'stroke-width': 1
    }));

    const text = svgEl('text', {
      x: margin.left - 12,
      y: y + 4,
      fill: '#64748b',
      'font-size': 12,
      'text-anchor': 'end'
    });

    text.textContent = tick;
    svg.appendChild(text);
  }

  const xLabel = svgEl('text', {
    x: width / 2,
    y: height - 16,
    fill: '#94a3b8',
    'font-size': 15,
    'text-anchor': 'middle'
  });
  xLabel.textContent = 'Número de neutrones N';
  svg.appendChild(xLabel);

  const yLabel = svgEl('text', {
    x: 18,
    y: height / 2,
    fill: '#94a3b8',
    'font-size': 15,
    'text-anchor': 'middle',
    transform: `rotate(-90 18 ${height / 2})`
  });
  yLabel.textContent = 'Número atómico Z';
  svg.appendChild(yLabel);

  for (const edge of currentChain.edges || []) {
    const source = byId[edge.from];
    const target = byId[edge.to];
    if (!source || !target) continue;

    const x1 = xScale(source.n);
    const y1 = yScale(source.z);
    const x2 = xScale(target.n);
    const y2 = yScale(target.z);

    const dx = x2 - x1;
    const dy = y2 - y1;
    const dist = Math.hypot(dx, dy) || 1;

    const padStart = 24;
    const padEnd = 32;

    const sx = x1 + (dx / dist) * padStart;
    const sy = y1 + (dy / dist) * padStart;
    const tx = x2 - (dx / dist) * padEnd;
    const ty = y2 - (dy / dist) * padEnd;

    const line = svgEl('line', {
      x1: sx,
      y1: sy,
      x2: tx,
      y2: ty,
      stroke: edgeColor(edge.mode),
      'stroke-width': 2.75,
      opacity: 0.92
    });

    const marker = markerForMode(edge.mode);
    if (marker) line.setAttribute('marker-end', marker);

    const title = svgEl('title');
    title.textContent = `${edge.from} -> ${edge.to} (${edge.mode}${edge.branch ? `, branch ${edge.branch}%` : ''})`;
    line.appendChild(title);
    svg.appendChild(line);
  }

  for (const nuclide of nuclides) {
    const x = xScale(nuclide.n);
    const y = yScale(nuclide.z);
    const selected = nuclide.id === selectedNuclideId;

    const g = svgEl('g', {
      class: 'nuclide',
      tabindex: 0
    });

    const circle = svgEl('circle', {
      cx: x,
      cy: y,
      r: 20,
      class: nuclide.stable ? 'stable-node' : 'radioactive-node'
    });

    circle.setAttribute(
      'stroke',
      selected ? '#facc15' : nuclide.stable ? '#22c55e' : '#64748b'
    );
    circle.setAttribute('stroke-width', selected ? 4 : 2);

    const symbolText = svgEl('text', {
      x,
      y: y + 5,
      fill: '#e2e8f0',
      'font-size': 13,
      'font-weight': 700,
      'text-anchor': 'middle'
    });
    symbolText.textContent = nuclide.symbol;

    const massText = svgEl('text', {
      x,
      y: y + 38,
      fill: '#94a3b8',
      'font-size': 12,
      'text-anchor': 'middle'
    });
    massText.textContent = nuclide.a;

    const title = svgEl('title');
    title.textContent = `${nuclide.name} | Z=${nuclide.z}, N=${nuclide.n}, A=${nuclide.a} | Vida media: ${nuclide.half_life || 'desconocida'}`;

    g.appendChild(circle);
    g.appendChild(symbolText);
    g.appendChild(massText);
    g.appendChild(title);

    g.addEventListener('click', () => {
      selectedNuclideId = nuclide.id;
      renderChart();
      renderTable();
      renderDetail(nuclide.id);
    });

    svg.appendChild(g);
  }

  chartEl.appendChild(svg);
}

function renderTable() {
  const tbody = document.querySelector('#nuclide-table tbody');
  if (!tbody || !currentChain) return;

  tbody.innerHTML = '';

  for (const nuclide of currentChain.nuclides || []) {
    const tr = document.createElement('tr');

    if (nuclide.id === selectedNuclideId) {
      tr.classList.add('selected');
    }

    const modes = (nuclide.decay_modes || []).join(', ') || '-';

    tr.innerHTML = `
      <td>${escapeHtml(nuclide.name || nuclide.id)}</td>
      <td>${nuclide.z}</td>
      <td>${nuclide.a - nuclide.z}</td>
      <td>${nuclide.a}</td>
      <td>${escapeHtml(nuclide.half_life || '-')}</td>
      <td>${escapeHtml(modes)}</td>
      <td>${nuclide.stable ? 'sí' : 'no'}</td>
    `;

    tr.addEventListener('click', () => {
      selectedNuclideId = nuclide.id;
      renderChart();
      renderTable();
      renderDetail(nuclide.id);
    });

    tbody.appendChild(tr);
  }
}

function renderDetail(nuclideId) {
  if (!currentChain) return;

  const nuclide = (currentChain.nuclides || []).find((item) => item.id === nuclideId);

  if (!nuclide) {
    detailEl.innerHTML = '<p>Selecciona un núclido.</p>';
    return;
  }

  const outgoing = (currentChain.edges || []).filter((edge) => edge.from === nuclide.id);
  const incoming = (currentChain.edges || []).filter((edge) => edge.to === nuclide.id);

  const modes = (nuclide.decay_modes || [])
    .map((mode) => `<span class="pill">${escapeHtml(mode)}</span>`)
    .join('') || '<span class="pill">-</span>';

  const outgoingHtml = outgoing.length
    ? outgoing
        .map((edge) => {
          return `<li>${escapeHtml(edge.to)} <span class="pill">${escapeHtml(edge.mode)}</span>${
            edge.branch ? ` (${escapeHtml(String(edge.branch))}%)` : ''
          }</li>`;
        })
        .join('')
    : '<li>-</li>';

  const incomingHtml = incoming.length
    ? incoming
        .map((edge) => {
          return `<li>${escapeHtml(edge.from)} <span class="pill">${escapeHtml(edge.mode)}</span>${
            edge.branch ? ` (${escapeHtml(String(edge.branch))}%)` : ''
          }</li>`;
        })
        .join('')
    : '<li>-</li>';

  detailEl.innerHTML = `
    <h2>${escapeHtml(nuclide.name || nuclide.id)}</h2>

    <div class="detail-label">Cadena</div>
    <div>${escapeHtml(currentChain.name)}</div>

    <div class="detail-label">Z / N / A</div>
    <div>${nuclide.z} / ${nuclide.a - nuclide.z} / ${nuclide.a}</div>

    <div class="detail-label">Vida media</div>
    <div>${escapeHtml(nuclide.half_life || '-')}</div>

    <div class="detail-label">Modos de decaimiento</div>
    <div>${modes}</div>

    <div class="detail-label">Decaimientos salientes</div>
    <ul>${outgoingHtml}</ul>

    <div class="detail-label">Decaimientos entrantes</div>
    <ul>${incomingHtml}</ul>

    <div class="detail-label">Nota</div>
    <div>${escapeHtml(ENDPOINTS.note)}</div>
  `;
}

// ---------- Búsqueda de núclidos (solo modo API: usa /api/nuclide/{Símbolo-A}) ----------

function initSearch() {
  // En la demo estática el formulario no existe: no hay nada que activar.
  if (!searchForm || MODE !== 'api' || !window.NuclideSearch) return;
  searchForm.addEventListener('submit', (event) => {
    event.preventDefault();
    runSearch(searchInput.value);
  });
}

async function runSearch(text) {
  const id = window.NuclideSearch.parseNuclideQuery(text);
  if (!id) {
    showSearchMessage(window.NuclideSearch.errorMessage(400, text), true);
    return;
  }

  const seq = ++searchSeq; // descarta respuestas antiguas si se lanza otra búsqueda
  const button = searchForm.querySelector('button');
  button.disabled = true;
  showSearchMessage(`Buscando ${id}…`, false);

  try {
    const res = await fetch(`/api/nuclide/${encodeURIComponent(id)}`);
    if (seq !== searchSeq) return;
    if (!res.ok) {
      showSearchMessage(window.NuclideSearch.errorMessage(res.status, id), true);
      return;
    }
    renderSearchResult(await res.json());
  } catch (error) {
    if (seq === searchSeq) showSearchMessage('No se pudo contactar con el servidor.', true);
  } finally {
    if (seq === searchSeq) button.disabled = false;
  }
}

function showSearchMessage(message, isError) {
  searchResultEl.hidden = false;
  searchResultEl.innerHTML = `<p class="${isError ? 'search-error' : 'search-info'}">${escapeHtml(message)}</p>`;
}

function renderSearchResult(nuclide) {
  const z = Number(nuclide.z);
  const a = Number(nuclide.a);
  const n = Number.isFinite(Number(nuclide.n)) ? Number(nuclide.n) : a - z;

  const modes = nuclide.stable
    ? '<span class="pill">estable</span>'
    : (nuclide.decay_modes || [])
        .map((mode) => `<span class="pill">${escapeHtml(mode)}</span>`)
        .join('') || '<span class="pill">-</span>';

  // Si el núclido pertenece a la cadena que se está viendo, se resalta en el gráfico.
  const isIsomer = /\d(m\d?)$/i.test(String(nuclide.id || ''));
  const inChain = (currentChain?.nuclides || []).some((item) => item.id === nuclide.id);
  if (inChain) {
    selectedNuclideId = nuclide.id;
    renderChart();
    renderTable();
    renderDetail(nuclide.id);
  }

  const daughters = (nuclide.decays_to || [])
    .map((d) => {
      const label = (d.modes || []).map((mode) => window.NuclideSearch.modeLabel(mode)).join(' / ');
      const id = escapeHtml(d.id);
      return `<li><span class="mode-tag">${escapeHtml(label)}</span> → <strong>${id}</strong>
        <button type="button" data-search="${id}">Ver ficha</button>
        <button type="button" data-levels="${id}">Niveles</button></li>`;
    })
    .join('');

  searchResultEl.hidden = false;
  searchResultEl.innerHTML = `
    <h2>${escapeHtml(nuclide.name || nuclide.id)}</h2>
    <div class="detail-label">Z / N / A</div>
    <div>${z} / ${n} / ${a}</div>
    <div class="detail-label">Vida media</div>
    <div>${escapeHtml(nuclide.half_life || '-')}</div>
    <div class="detail-label">Modos de decaimiento</div>
    <div>${modes}</div>
    <div class="detail-label">Fuente</div>
    <div>${escapeHtml(nuclide.source || '-')}</div>
    ${daughters ? `<div class="detail-label">Decae a</div><ul class="daughters">${daughters}</ul>` : ''}
    ${inChain ? '<p class="search-info">También está en la cadena actual: se ha seleccionado en el gráfico.</p>' : ''}
    ${isIsomer ? '' : '<p><button type="button" id="levels-button">Ver esquema de niveles</button></p>'}
  `;
  searchResultEl.querySelectorAll('button[data-search]').forEach((button) => {
    button.addEventListener('click', () => {
      searchInput.value = button.dataset.search;
      runSearch(button.dataset.search);
    });
  });
  searchResultEl.querySelectorAll('button[data-levels]').forEach((button) => {
    button.addEventListener('click', () => loadLevels(button.dataset.levels, 20));
  });
  const levelsButton = searchResultEl.querySelector('#levels-button');
  if (levelsButton) levelsButton.addEventListener('click', () => loadLevels(nuclide.id, 20));
}

// ---------- Exportar el gráfico (SVG / PNG): funciona en modo API y en la demo estática ----------

function initExport() {
  const svgButton = document.getElementById('export-svg');
  const pngButton = document.getElementById('export-png');
  if (!svgButton || !pngButton || !window.NuclideExport) return;
  svgButton.addEventListener('click', () => exportChart('svg'));
  pngButton.addEventListener('click', () => exportChart('png'));
}

function setExportStatus(message) {
  const status = document.getElementById('export-status');
  if (status) status.textContent = message;
}

async function exportChart(kind) {
  const svg = chartEl.querySelector('svg');
  if (!svg || !currentChain) {
    setExportStatus('No hay gráfico que exportar todavía.');
    return;
  }
  setExportStatus('');
  try {
    const { markup, width, height } = window.NuclideExport.serializeChart(svg, {
      title: currentChain.name
    });
    const name = window.NuclideExport.exportFileName(currentChain.id || selectEl.value, kind);
    if (kind === 'svg') {
      downloadBlob(new Blob([markup], { type: 'image/svg+xml;charset=utf-8' }), name);
    } else {
      downloadBlob(await svgToPngBlob(markup, width, height), name);
    }
  } catch (error) {
    setExportStatus(
      kind === 'png'
        ? 'No se pudo generar el PNG en este navegador. Prueba con SVG.'
        : 'No se pudo exportar el gráfico.'
    );
  }
}

function svgToPngBlob(markup, width, height) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      canvas.getContext('2d').drawImage(img, 0, 0, width, height);
      canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('toBlob'))), 'image/png');
    };
    img.onerror = () => reject(new Error('No se pudo rasterizar el SVG'));
    // data: URL (no blob:) para que el canvas no quede "contaminado" y permita toBlob.
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(markup);
  });
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------- Esquema de niveles (solo modo API: /api/nuclide/{id}/levels) ----------

async function loadLevels(id, maxLevels) {
  if (!levelsPanelEl || !window.NuclideLevels) return;
  const seq = ++levelsSeq;
  levelsPanelEl.hidden = false;
  levelsPanelEl.innerHTML = `<p class="search-info">Cargando niveles de ${escapeHtml(id)}…</p>`;
  try {
    const res = await fetch(`/api/nuclide/${encodeURIComponent(id)}/levels?max_levels=${maxLevels}`);
    if (seq !== levelsSeq) return;
    if (!res.ok) {
      const message = res.status === 404
        ? `IAEA no tiene datos de niveles para ${id}.`
        : res.status === 502
          ? 'El servicio remoto de IAEA no está disponible ahora mismo. Inténtalo más tarde.'
          : `Error inesperado del servidor (HTTP ${res.status}).`;
      levelsPanelEl.innerHTML = `<p class="search-error">${escapeHtml(message)}</p>`;
      return;
    }
    renderLevelsPanel(await res.json(), maxLevels);
  } catch (error) {
    if (seq === levelsSeq) {
      levelsPanelEl.innerHTML = '<p class="search-error">No se pudo contactar con el servidor.</p>';
    }
  }
}

function renderLevelsPanel(data, maxLevels) {
  const omitted = Number(data.omitted_shifted) || 0;
  const options = [10, 20, 40, 80]
    .map((v) => `<option value="${v}"${v === maxLevels ? ' selected' : ''}>${v}</option>`)
    .join('');
  levelsPanelEl.hidden = false;
  levelsPanelEl.innerHTML = `
    <div class="levels-head">
      <h2>Esquema de niveles: ${escapeHtml(data.name || data.id)}</h2>
      <label>Niveles <select id="levels-max">${options}</select></label>
      <button type="button" id="levels-export">Exportar SVG</button>
    </div>
    <p class="search-info">
      Mostrando ${Number(data.shown_levels)} de ${Number(data.total_levels)} niveles (los de menor energía)${omitted ? ` · ${omitted} omitidos por energía no determinada` : ''}.
      Son niveles del propio núclido: las transiciones de un decaimiento (p. ej. Co-60 → Ni-60) se ven en el núclido hijo.
    </p>
    <div id="levels-svg"></div>
  `;
  const svg = window.NuclideLevels.renderLevelScheme(data, document);
  levelsPanelEl.querySelector('#levels-svg').appendChild(svg);
  levelsPanelEl.querySelector('#levels-max').addEventListener('change', (event) => {
    loadLevels(data.id, Number(event.target.value));
  });
  levelsPanelEl.querySelector('#levels-export').addEventListener('click', () => {
    try {
      const { markup } = window.NuclideExport.serializeChart(svg, { title: `${data.name || data.id} · niveles` });
      downloadBlob(
        new Blob([markup], { type: 'image/svg+xml;charset=utf-8' }),
        window.NuclideExport.exportFileName(`${data.id}-niveles`, 'svg')
      );
    } catch (error) {
      levelsPanelEl.querySelector('.search-info').textContent = 'No se pudo exportar el esquema.';
    }
  });
}
