// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) Pedro Sordo Martínez

// Parseo de la consulta del usuario y mensajes de error de la búsqueda de núclidos.
// Sin dependencias del DOM: se carga en el navegador y se prueba con node.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.NuclideSearch = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const SYMBOL_FIRST = /^([A-Za-z]{1,2})\s*-?\s*(\d{1,3})([mM]\d?)?$/; // Pb-214, pb214, Pa-234m
  const MASS_FIRST = /^(\d{1,3})([mM]\d?)?\s*-?\s*([A-Za-z]{1,2})$/;   // 214Pb, 99mTc, 214-pb

  function canonical(symbol, mass, isomer) {
    const a = parseInt(mass, 10);
    if (!(a >= 1 && a <= 300)) return null;
    const sym = symbol.charAt(0).toUpperCase() + symbol.slice(1).toLowerCase();
    return `${sym}-${a}${isomer ? isomer.toLowerCase() : ''}`;
  }

  // Devuelve "Símbolo-A[m]" (p. ej. "Pb-214", "Pa-234m") o null si el formato no es válido.
  function parseNuclideQuery(text) {
    const q = String(text || '').trim();
    let m = SYMBOL_FIRST.exec(q);
    if (m) return canonical(m[1], m[2], m[3]);
    m = MASS_FIRST.exec(q);
    if (m) return canonical(m[3], m[1], m[2]);
    return null;
  }

  function errorMessage(status, id) {
    if (status === 400) return 'Formato no válido. Prueba con Pb-214, 214Pb o Pa-234m.';
    if (status === 404) return `${id} no existe en el dataset local ni en IAEA (o es un isómero sin datos locales).`;
    if (status === 502) return 'El servicio remoto de IAEA no está disponible ahora mismo. Inténtalo más tarde.';
    return `Error inesperado del servidor (HTTP ${status}).`;
  }

  return { parseNuclideQuery, errorMessage };
});
