// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) Pedro Sordo Martínez

// Exportación del gráfico de la cadena a SVG autónomo (y base para PNG).
// El SVG de la página depende de reglas de style.css; aquí se incrustan para que el
// archivo exportado se vea igual fuera de la página.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.NuclideExport = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const FONT_FAMILY = 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif';
  const BACKGROUND = '#020617';
  // Rellenos que en la página vienen de style.css (.stable-node / .radioactive-node).
  const CLASS_FILLS = { 'stable-node': '#052e16', 'radioactive-node': '#082f49' };

  // "nuclear-viz-u238.svg"; solo caracteres seguros para nombres de archivo.
  function exportFileName(chainId, ext) {
    const slug = String(chainId || '')
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'cadena';
    return `nuclear-viz-${slug}.${ext}`;
  }

  // Devuelve { markup, width, height } con un SVG autocontenido a partir del <svg> de la página.
  function serializeChart(svg, opts = {}) {
    const scale = opts.scale || 2;
    const parts = svg.getAttribute('viewBox').trim().split(/\s+/).map(Number);
    const vbW = parts[2];
    const vbH = parts[3];
    if (!(vbW > 0 && vbH > 0)) throw new Error('viewBox no válido');

    const doc = svg.ownerDocument;
    const clone = svg.cloneNode(true);
    clone.setAttribute('width', String(vbW * scale));
    clone.setAttribute('height', String(vbH * scale));
    clone.setAttribute('font-family', FONT_FAMILY);
    clone.querySelectorAll('[tabindex]').forEach((el) => el.removeAttribute('tabindex'));
    clone.querySelectorAll('circle').forEach((circle) => {
      for (const [cls, fill] of Object.entries(CLASS_FILLS)) {
        if (circle.classList.contains(cls) && !circle.getAttribute('fill')) {
          circle.setAttribute('fill', fill);
        }
      }
    });

    const bg = doc.createElementNS(SVG_NS, 'rect');
    bg.setAttribute('width', '100%');
    bg.setAttribute('height', '100%');
    bg.setAttribute('fill', BACKGROUND);
    clone.insertBefore(bg, clone.firstChild);

    const credit = doc.createElementNS(SVG_NS, 'text');
    credit.setAttribute('x', String(vbW - 12));
    credit.setAttribute('y', String(vbH - 8));
    credit.setAttribute('text-anchor', 'end');
    credit.setAttribute('font-size', '11');
    credit.setAttribute('fill', '#475569');
    credit.textContent = opts.title ? `Nuclear Viz · ${opts.title}` : 'Nuclear Viz';
    clone.appendChild(credit);

    const serializer = new (doc.defaultView.XMLSerializer)();
    const markup = '<?xml version="1.0" encoding="UTF-8"?>\n' + serializer.serializeToString(clone);
    return { markup, width: vbW * scale, height: vbH * scale };
  }

  return { exportFileName, serializeChart, CLASS_FILLS };
});
