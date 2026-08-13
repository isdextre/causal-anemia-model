# Diccionario de datos — `panel_distrital_final.csv`

**Ruta:** `data/clean/merged/panel_distrital_final.csv`
**Grano:** distrito (`ubigeo`) × año (`anio`)
**Shape verificado en esta sesión:** 13,148 filas × 36 columnas
**Cobertura temporal:** 2020-2026 (según la fuente, no todas las columnas cubren todo el rango — ver tabla)
**Ubigeos únicos:** 1891 (1889 del universo `geobase_distrital.gpkg` + 2 sin match territorial, ver Limitaciones)
**Duplicados en la clave `ubigeo + anio`:** 0

Este documento describe cada columna con su definición oficial, unidad, fuente, nivel de granularidad real y nulos verificados contra el archivo actual. Sirve como base para la sección de metodología/limitaciones de la aplicación final.

---

## Llaves

| Columna | Tipo | Descripción |
|---|---|---|
| `ubigeo` | string, 6 dígitos | Código INEI de distrito (departamento-provincia-distrito, 2 dígitos cada uno), con ceros a la izquierda preservados. |
| `anio` | int | Año de referencia de la fila. **Su significado exacto varía por grupo de variables** — ver nota en cada bloque abajo. |

---

## Variable dependiente — anemia infantil (SIEN/HIS-MINSA vía REUNIS)

Fuente: `Trama_Base_Anemia.xlsx` (MINSA), tamizajes de hemoglobina, filtrados a **menores de 3 años** (`Edad == 1`), agregados por `ubigeo` + `Año`.

| Columna | Tipo | Definición | Nulos | Nota |
|---|---|---|---|---|
| `ninos_evaluados` | float | Suma de niños menores de 3 años evaluados (tamizados) en el distrito ese año | 119 | Cobertura real: 2020-2026 |
| `ninos_con_anemia` | float | Suma de niños con resultado de anemia (cualquier severidad) | 119 | |
| `ninos_sin_anemia` | float | Suma de niños con resultado normal | 119 | |
| `prevalencia_anemia` | float [0-1] | `ninos_con_anemia / ninos_evaluados` | 161 | Los 119 anteriores + casos con `ninos_evaluados = 0` (división por cero) |

**`anio` para este bloque = año del tamizaje**, tal como lo reporta SIEN.

**Limitación conocida (documentada en la bitácora del proyecto):** el registro es administrativo, no un censo — refleja quién llegó a tamizarse, no necesariamente la prevalencia real del distrito. La corrección de este sesgo de selección (vía ENDES) es un paso pendiente del pipeline, todavía no aplicado a esta tabla.

---

## Variable de tratamiento — gasto público (SIAF, MEF)

Fuente: "Presupuesto y Ejecución de Gasto — Devengado Mensual" (MEF), fase contable **Devengado** (el bien/servicio ya fue recibido, obligación de pago reconocida). Agregado por `ubigeo` + `ANO_EJE`.

| Columna | Tipo | Definición | Nulos | Nota |
|---|---|---|---|---|
| `gasto_total` | float, soles | Suma del monto devengado anual, **todos** los programas presupuestales, de la(s) unidad(es) ejecutora(s) ubicada(s) en ese distrito | 3696 | Cobertura real: 2021-2025 |
| `gasto_anemia_pan` | float, soles | Mismo cálculo, filtrado solo a `PROGRAMA_PPTO = 0001` (Programa Articulado Nutricional). `0` si el distrito no ejecutó nada en PAN ese año (no `NaN`) | 3696 | Solo cubre PAN — no incluye salud materno-neonatal, saneamiento rural, Cuna Más, Qali Warma, JUNTOS ni incentivos municipales, que el documento maestro también identifica como programas con incidencia en anemia |

**`anio` para este bloque = `ANO_EJE`, año de ejecución presupuestal.**

**Limitaciones conocidas:**
- El `ubigeo` de esta tabla identifica **dónde está registrada la unidad ejecutora del gasto**, no necesariamente el distrito donde se presta el servicio. Una unidad ejecutora regional puede estar en la capital de provincia y administrar gasto que en la práctica se ejecuta en distritos rurales alrededor. Es un proxy, declarado explícitamente como limitación en el notebook fuente.
- Los montos están en soles absolutos, **sin normalizar por población infantil**. Un distrito con más niños menores de 3 mostrará una relación gasto-anemia distinta solo por efecto de denominador — normalización pendiente (requiere el Padrón Nominal de REUNIS).
- Se excluyó `160405` (Santa Rosa de Loreto, distrito creado julio 2025, no existe en el shapefile INEI de referencia) — S/ 402,358.70 excluidos del total nacional.
- 3 combinaciones ubigeo-año (`2021-180107`, `2021-130112`, `2022-130112`) no tienen ninguna fila en SIAF; quedan como `NaN`, no investigadas todavía.

---

## Variables de control — gestión municipal (RENAMU, INEI)

Función: evitar que el modelo confunda "el gasto no rinde por el territorio" con "el gasto no rinde por mala gestión municipal". Fuente verificada contra el diccionario oficial (`Diccionario_Anexo01.pdf`, RENAMU 2021).

| Columna | Tipo | Código de pregunta | Definición oficial | Nulos |
|---|---|---|---|---|
| `personal_total` | float | P19D_T | "Total personal / 31 de diciembre [año]" — headcount total de personal municipal | 5812 |
| `programa_anemia` | float (0/1) | P68_10 | *"¿La municipalidad implementó programas de control y prevención de la salud en coordinación con el MINSA en: Prevención y reducción de la anemia"* — 1 = Sí, 0 = No/no aplica | 5622 |
| `centro_salud_municipal` | float (0/1) | P66_2 | *"¿En el Distrito funcionan establecimientos de salud administrados por la Municipalidad: Centro de salud?"* — 1 = Sí, 0 = No | 5622 |

Cobertura real: 2021-2024 (el módulo de anemia recién existe desde 2021).

**⚠️ Limitación crítica no resuelta en el archivo actual:** `personal_total` y `programa_anemia` son preguntas **retrospectivas** — describen el año *anterior* al `anio` de la fila (ej. la fila `anio=2021` en realidad describe diciembre de 2020), mientras que `centro_salud_municipal` describe el año de la encuesta directamente (sin desfase). **Esta corrección de año (`anio - 1` para las dos primeras) todavía no se aplicó en el merge**, por lo que hoy estas dos columnas están comparándose contra el gasto y la anemia del año equivocado. Debe corregirse antes de usar esta tabla en el modelo causal.

También pendiente sin confirmar: que el código `10 = Sí` de `programa_anemia` se mantiene igual en los diccionarios RENAMU 2022-2025 (no verificado con `value_counts()` año por año).

---

## Contexto territorial — identidad y ubicación (`geobase_distrital.gpkg`)

Una fila por distrito, repetida idéntica para todos los años de ese distrito en el panel (variables time-invariant). Universo: 1889 distritos válidos (INEI 2025 CPV, con 5 exclusiones documentadas por discrepancia shapefile/tabla censal).

| Columna | Tipo | Definición | Nulos |
|---|---|---|---|
| `departamento`, `provincia`, `distrito` | string | Nombre administrativo | 9 |
| `region` | string | Región geográfica (costa/sierra/selva u homóloga) | 9 |
| `macroregion_inei`, `macroregion_minsa` | string | Agrupaciones macro-regionales según INEI y MINSA respectivamente (pueden diferir entre sí) | 9 |
| `capital` | string | Nombre de la capital distrital | 97 |
| `latitude`, `longitude` | float | Coordenadas del distrito | 97 |
| `altitude` | float, msnm | Altitud. **No decorativa**: OMS/MINSA ajustan el punto de corte de hemoglobina según altitud — necesaria para interpretar correctamente `prevalencia_anemia` entre distritos de distinta altura | 97 |
| `superficie` | float, km² | Superficie del distrito | 125 |
| `pob_densidad_2020` | float, hab/km² | Densidad poblacional 2020 | 125 |

**Nulos explicados:**
- `departamento`...`macroregion_minsa` (9 filas): corresponden a `130112` y `180107`, dos ubigeos presentes en `sien_reunis`/`renamu` que **no existen** en `geobase_distrital.gpkg` — probablemente distritos creados o reorganizados después del corte del shapefile de referencia (mismo fenómeno que `160405` en SIAF, no investigado todavía).
- `capital`/`latitude`/`longitude`/`altitude` (97) y `superficie`/`pob_densidad_2020` (125): las 9 filas anteriores **más** 15 distritos que ya tenían estos campos vacíos en el propio `geobase_distrital.gpkg` de origen (ej. Ahuayro, Putis, Unión Progreso, Kumpirushiatro, Unión Asháninka — mayoría zonas remotas de selva/sierra), replicados por cada año en que aparecen en el panel. **Verificado en esta sesión: no es un error de conversión de tipos** (`superficie`/`pob_densidad_2020` se leyeron en el `.gpkg` como texto y se convirtieron a número sin ningún fallo de parseo) — es un vacío real de la fuente censal/geográfica.

---

## Contexto territorial — cobertura de suelo (ESA WorldCover 2021, satelital)

| Columna | Tipo | Definición | Nulos |
|---|---|---|---|
| `pct_cultivo` | float [0-1] | % de superficie distrital clasificada como cultivo activo | 9 |
| `pct_construido` | float [0-1] | % clasificado como área construida | 9 |
| `pct_desnudo` | float [0-1] | % clasificado como suelo desnudo | 9 |
| `pct_agua_visible` | float [0-1] | % clasificado como cuerpo de agua visible | 9 |

Nulos: solo los 2 ubigeos sin match en geobase.

## Contexto territorial — edificaciones (Google Open Buildings V3, satelital)

Proxy directo de **dispersión de viviendas** — variable central del argumento del proyecto: viviendas concentradas facilitan el seguimiento domiciliario del programa de hierro, dispersas lo dificultan.

| Columna | Tipo | Definición | Nulos |
|---|---|---|---|
| `n_edificios` | float | Conteo de edificaciones detectadas en el distrito | 9 |
| `area_construida_m2` | float, m² | Área total construida | 9 |
| `confianza_media` | float [0-1] | Confianza media del modelo de detección de Open Buildings | 9 |
| `area_distrito_km2` | float, km² | Área total del distrito (para el cálculo de densidad) | 9 |
| `densidad_edificios_km2` | float | `n_edificios / area_distrito_km2` | 9 |

## Contexto territorial — elevación y pendiente (SRTM 30m, satelital)

| Columna | Tipo | Definición | Nulos |
|---|---|---|---|
| `elevacion_media` | float, msnm | Elevación media del distrito | 9 |
| `pendiente_media` | float, grados | Pendiente media del terreno — proxy de accesibilidad logística | 9 |

## Contexto territorial — agua (JRC Global Surface Water, satelital)

| Columna | Tipo | Definición | Nulos |
|---|---|---|---|
| `pct_agua_permanente` | float [0-1] | % de superficie con agua detectada de forma permanente | 9 |
| `pct_agua_estacional` | float [0-1] | % de superficie con agua detectada de forma estacional | 9 |

**Nota de diseño:** la fuente JRC solo cubre 1806 de 1889 distritos; los 83 restantes se rellenaron con `0` explícitamente durante el merge (interpretados como "sin agua detectada", no como dato faltante). Los 9 nulos que sí aparecen aquí corresponden únicamente a los 2 ubigeos sin match en geobase — el `fillna(0)` funcionó como se diseñó.

---

## Resumen de limitaciones para trasladar a la pantalla de metodología/limitaciones de la app

1. **Sesgo de selección en anemia:** el registro SIEN es administrativo (quién llegó a tamizarse), no un censo — pendiente de corrección con ENDES.
2. **Gasto no normalizado por población infantil** — soles absolutos, no per cápita.
3. **UBIGEO de SIAF = unidad ejecutora, no necesariamente distrito de intervención real.**
4. **Desfase de año sin corregir en `personal_total`/`programa_anemia`** (RENAMU) — corrección pendiente de aplicar.
5. **2 ubigeos (`130112`, `180107`) sin contexto territorial** por no estar en `geobase_distrital.gpkg` — 9 filas del panel incompletas.
6. **15 distritos con vacíos de origen** en coordenadas/superficie/densidad (no error del pipeline).
7. **`gasto_anemia_pan` solo cubre PAN (0001)**, no los demás programas con incidencia en anemia que menciona el documento maestro.
8. **Sesgo de agregación ecológica:** el contexto territorial describe el distrito completo, la anemia describe solo menores de 3 años — argumentado como tolerable a nivel de caserío rural, pero debe declararse.
9. **Solo 1806/1889 distritos tienen dato JRC directo**, el resto se imputó a 0.
