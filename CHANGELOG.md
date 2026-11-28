# Historial de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Las versiones anteriores a la 0.3.3 (0.2.0 a 0.3.2) están en las etiquetas y el historial de git.

## [0.7.0] - 2026-11-28

### Añadido
- Núcleo hijo en la ficha de un núclido: «Decae a» (α, β⁻, β⁺ y captura electrónica) con atajos a la
  ficha del hijo y a su esquema de niveles. La API expone el campo `decays_to` en `/api/nuclide/{Símbolo-A}`.

### Corregido
- El esquema de niveles de núclidos como el Ni-60 daba un 502: los datos reales de IAEA incluyen
  alguna transición sin nivel de destino, y una fila incompleta invalidaba toda la respuesta.
  Ahora esas filas se omiten y se cuentan en `skipped_rows`.

## [0.6.0] - 2026-11-28

### Añadido
- Esquema de niveles y transiciones gamma desde la ficha de búsqueda (modo servidor): niveles de energía,
  flechas con grosor según la intensidad relativa, selector de 10, 20, 40 u 80 niveles y exportación a SVG.
- Endpoint `GET /api/nuclide/{Símbolo-A}/levels?max_levels=40` (de 5 a 100 niveles), con caché.

### Corregido
- Un error numérico de IAEA (códigos 1 a 6) ya no se confunde con «el núclido no existe» (código 0):
  ahora produce un 502 o, si lo hay, devuelve el dato local.

### Documentación
- README con guía de uso, tabla de la API, estructura del repositorio y gráficos de ejemplo
  exportados con la propia aplicación (`docs/ejemplos/`), más tests que evitan que se desincronicen.

## [0.5.0] - 2026-11-27

### Añadido
- Botones «Exportar SVG» y «Exportar PNG» (2200×1520) del gráfico de la cadena, en el modo servidor
  y en la demo estática.
- La demo estática avisa de que la búsqueda de núclidos requiere el servidor local.

## [0.4.0] - 2026-11-27

### Añadido
- Búsqueda de núclidos en la interfaz (modo servidor), con los formatos `Pb-214`, `pb214`, `214Pb`
  y `Pa-234m`.

### Cambiado
- El frontend tiene una única fuente en `site/`; cada página declara su modo (`api` o `static`).
- El lema del proyecto y el ☢ amarillo aparecen en la cabecera de las dos páginas.
- La vida media usa exponente en minúscula (`4.468e9 y`).

### Seguridad
- Los datos recibidos del servidor se escapan antes de mostrarse en la página.

## [0.3.3] - 2026-11-27

### Cambiado
- El cliente de NNDC, cuyo endpoint no existía, se sustituye por IAEA Livechart (datos ENSDF), con caché
  de 1 hora y respuestas 404 («no existe») y 502 («servicio no disponible») diferenciadas.
- La tabla de elementos llega hasta el Og (Z = 118).
- `run.sh` escucha por defecto solo en `127.0.0.1` (`HOST=0.0.0.0` para la red local) y CORS se limita a `GET`.
- La versión se define solo en `pyproject.toml`.

### Corregido
- Los símbolos de dos letras (`Pb`, `Th`…) daban 404 en `/api/nuclide`.
- Los isómeros (`Pa-234m`) se rechazaban con 400.
- Los nombres de modos de decaimiento no reconocidos se etiquetaban como captura electrónica.
