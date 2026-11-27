// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) Pedro Sordo Martínez

// Esquema de niveles de un núclido: geometría (pura, testeable con node) y dibujo SVG.
// Entrada: respuesta de /api/nuclide/{id}/levels ({ levels: [...], gammas: [...] }).
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.NuclideLevels = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const W = 900;
  const H = 640;
  const PLOT = { top: 44, bottom: 590, axisX: 70, lineX1: 90, lineX2: 560, labelX: 590 };
  const LABEL_BOUNDS = { lo: 28, hi: 600 };
  const MAX_LABEL_GAP = 14;
  const ARROW_COLOR = '#38bdf8';

  function niceStep(raw) {
    const pow = Math.pow(10, Math.floor(Math.log10(raw)));
    const f = raw / pow;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * pow;
  }

  function fmtEnergy(energy) {
    return String(Number(Number(energy).toFixed(1)));
  }

  // Separa las etiquetas verticalmente (y decrece al subir la energía) garantizando `gap` px.
  function spreadLabels(ys, gap, lo, hi) {
    const p = ys.slice();
    for (let i = 1; i < p.length; i++) p[i] = Math.min(p[i], p[i - 1] - gap); // hacia arriba
    if (p.length) {
      p[p.length - 1] = Math.max(p[p.length - 1], lo); // tope superior
      for (let i = p.length - 2; i >= 0; i--) p[i] = Math.max(p[i], p[i + 1] + gap); // hacia abajo
    }
    return p.map((v) => Math.min(v, hi));
  }

  function layoutLevelScheme(data) {
    const levels = (data.levels || []).slice().sort((a, b) => a.energy - b.energy || a.idx - b.idx);
    const n = levels.length;
    const maxE = n ? Math.max(levels[n - 1].energy, 0) : 0;
    const scale = maxE > 0 ? (PLOT.bottom - PLOT.top) / maxE : 0;
    const yOf = (energy) => PLOT.bottom - energy * scale;

    // Con muchos niveles el hueco entre etiquetas se reduce (y la fuente con él).
    const room = LABEL_BOUNDS.hi - LABEL_BOUNDS.lo;
    const labelGap = n > 1 ? Math.min(MAX_LABEL_GAP, room / (n - 1)) : MAX_LABEL_GAP;
    const labelFont = Math.min(11, Math.max(6, labelGap - 2));
    const labelYs = spreadLabels(levels.map((lv) => yOf(lv.energy)), labelGap, LABEL_BOUNDS.lo, LABEL_BOUNDS.hi);

    const laidLevels = levels.map((lv, i) => {
      const e = fmtEnergy(lv.energy);
      const parts = [lv.jp, `${e} keV`, lv.half_life].filter(Boolean);
      return {
        idx: lv.idx,
        energy: lv.energy,
        y: yOf(lv.energy),
        labelY: labelYs[i],
        x1: PLOT.lineX1,
        x2: PLOT.lineX2,
        text: parts.join(' · '),
        title: `Nivel ${lv.idx}: ${parts.join(' · ')}`,
        ground: lv.energy === 0
      };
    });
    const byIdx = new Map(laidLevels.map((lv) => [lv.idx, lv]));

    const gammas = (data.gammas || [])
      .filter((g) => byIdx.has(g.start) && byIdx.has(g.end))
      .sort((a, b) => byIdx.get(a.start).energy - byIdx.get(b.start).energy || a.energy - b.energy);
    const x0 = PLOT.lineX1 + 14;
    const x1 = PLOT.lineX2 - 14;
    const step = gammas.length > 1 ? Math.min(34, (x1 - x0) / (gammas.length - 1)) : 0;
    const startX = gammas.length > 1 ? x0 + (x1 - x0 - step * (gammas.length - 1)) / 2 : (x0 + x1) / 2;
    const showAll = gammas.length <= 12;

    const laidGammas = gammas.map((g, i) => {
      const known = typeof g.intensity === 'number';
      const width = known ? 0.8 + (1.7 * Math.log10(1 + Math.min(g.intensity, 100))) / Math.log10(101) : 0.8;
      const mult = g.multipolarity ? ` ${g.multipolarity}` : '';
      return {
        x: startX + i * step,
        y1: byIdx.get(g.start).y,
        y2: byIdx.get(g.end).y,
        width,
        dashed: !known,
        energy: g.energy,
        label: fmtEnergy(g.energy),
        showLabel: step >= 12 && (showAll || (known && g.intensity >= 50)),
        title: `γ ${fmtEnergy(g.energy)} keV${mult}${known ? ` · I = ${g.intensity}` : ''}`
      };
    });

    const ticks = [];
    if (maxE > 0) {
      const tickStep = niceStep(maxE / 5);
      for (let t = 0; t <= maxE + 1e-9; t += tickStep) ticks.push({ value: t, y: yOf(t), label: fmtEnergy(t) });
    } else {
      ticks.push({ value: 0, y: yOf(0), label: '0' });
    }

    const shown = Number(data.shown_levels) || n;
    const total = Number(data.total_levels) || n;
    return {
      width: W,
      height: H,
      plot: PLOT,
      labelGap,
      labelFont,
      title: `${data.name || data.id || ''} · niveles ${shown} de ${total} (menor energía)`.trim(),
      levels: laidLevels,
      gammas: laidGammas,
      ticks
    };
  }

  function el(doc, name, attrs, text) {
    const node = doc.createElementNS(SVG_NS, name);
    for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // Dibuja el esquema. Todo el estilo va en atributos: el SVG es autónomo al exportarlo.
  function renderLevelScheme(data, doc) {
    const g = layoutLevelScheme(data);
    const svg = el(doc, 'svg', {
      viewBox: `0 0 ${g.width} ${g.height}`,
      role: 'img',
      'aria-label': `Esquema de niveles de ${data.name || data.id || 'núclido'}`
    });

    const defs = el(doc, 'defs');
    const marker = el(doc, 'marker', {
      id: 'lv-arrow', viewBox: '0 0 10 10', refX: 9, refY: 5,
      markerWidth: 7, markerHeight: 7, markerUnits: 'userSpaceOnUse', orient: 'auto'
    });
    marker.appendChild(el(doc, 'path', { d: 'M 0 0 L 10 5 L 0 10 z', fill: ARROW_COLOR }));
    defs.appendChild(marker);
    svg.appendChild(defs);

    svg.appendChild(el(doc, 'text', { x: g.plot.axisX, y: 20, fill: '#e2e8f0', 'font-size': 14, 'font-weight': 600 }, g.title));

    // Eje de energía
    svg.appendChild(el(doc, 'line', { x1: g.plot.axisX, y1: g.plot.bottom, x2: g.plot.axisX, y2: g.plot.top, stroke: '#475569' }));
    svg.appendChild(el(doc, 'text', { x: g.plot.axisX - 6, y: g.plot.top - 12, fill: '#64748b', 'font-size': 11, 'text-anchor': 'end' }, 'keV'));
    for (const t of g.ticks) {
      svg.appendChild(el(doc, 'line', { x1: g.plot.axisX - 4, y1: t.y, x2: g.plot.axisX, y2: t.y, stroke: '#475569' }));
      svg.appendChild(el(doc, 'text', { x: g.plot.axisX - 8, y: t.y + 4, fill: '#64748b', 'font-size': 10, 'text-anchor': 'end' }, t.label));
    }

    // Niveles y etiquetas (con línea guía si la etiqueta se desplazó)
    for (const lv of g.levels) {
      const level = el(doc, 'g');
      level.appendChild(el(doc, 'title', {}, lv.title));
      level.appendChild(el(doc, 'line', {
        x1: lv.x1, y1: lv.y, x2: lv.x2, y2: lv.y,
        stroke: lv.ground ? '#94a3b8' : '#e2e8f0', 'stroke-width': lv.ground ? 2.5 : 1.5
      }));
      if (Math.abs(lv.labelY - lv.y) > 1) {
        level.appendChild(el(doc, 'polyline', {
          points: `${lv.x2},${lv.y} ${lv.x2 + 12},${lv.labelY}`, fill: 'none', stroke: '#334155'
        }));
      }
      level.appendChild(el(doc, 'text', {
        x: g.plot.labelX - 16 + 6, y: lv.labelY + g.labelFont * 0.35, fill: '#cbd5e1', 'font-size': g.labelFont
      }, lv.text));
      svg.appendChild(level);
    }

    // Transiciones gamma
    for (const gm of g.gammas) {
      const arrow = el(doc, 'g');
      arrow.appendChild(el(doc, 'title', {}, gm.title));
      const attrs = {
        x1: gm.x, y1: gm.y1, x2: gm.x, y2: gm.y2, stroke: ARROW_COLOR,
        'stroke-width': gm.width, 'marker-end': 'url(#lv-arrow)', 'stroke-opacity': gm.dashed ? 0.6 : 0.9
      };
      if (gm.dashed) attrs['stroke-dasharray'] = '4 3';
      arrow.appendChild(el(doc, 'line', attrs));
      if (gm.showLabel) {
        const ym = (gm.y1 + gm.y2) / 2;
        arrow.appendChild(el(doc, 'text', {
          x: gm.x + 4, y: ym, fill: '#7dd3fc', 'font-size': 9, 'text-anchor': 'middle',
          transform: `rotate(-90 ${gm.x + 4} ${ym})`
        }, gm.label));
      }
      svg.appendChild(arrow);
    }
    return svg;
  }

  return { layoutLevelScheme, renderLevelScheme, spreadLabels, niceStep, fmtEnergy };
});
