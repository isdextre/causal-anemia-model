# Bitácora completa — causal-anemia-model

De la ingesta cruda (`data/raw/`) al panel distrital unido (`data/clean/merged/panel_distrital_final.csv`), notebooks `00a` a `00i` (`notebooks/01_database/`) y el merge (`notebooks/02_anemia_and_spending_models/00a_mergue_database.ipynb`).

Consolidada a partir de las bitácoras `00a-00f`, `00g_renamu`, `00h_sien_reunis` ya guardadas en el proyecto, más lectura directa de los notebooks `00h`, `00i`, los diccionarios de datos oficiales (RENAMU `Diccionario_Anexo01.pdf`, SIAF `Gasto_Devengado_Diccionario.csv`), y una validación programática del archivo `panel_distrital_final.csv` actual en disco.

---

## 0. Convenciones generales (aplican a todos los notebooks de `01_database`)

1. **Cada notebook corre en su propio kernel.** Nunca se asume que una variable de otro notebook ya existe en memoria; cada uno carga sus datos desde disco.
2. **Bloque de rutas robusto**, al inicio de cada notebook, para no depender de rutas relativas que se rompen según la subcarpeta:
   ```python
   from pathlib import Path

   def find_project_root(marker="requirements.txt"):
       path = Path.cwd()
       for parent in [path] + list(path.parents):
           if (parent / marker).exists():
               return parent
       raise FileNotFoundError(f"No se encontró '{marker}' subiendo desde {path}")

   PROJECT_ROOT = find_project_root()
   DATA = PROJECT_ROOT / "data"
   ```
3. **Fuente única de verdad geográfica:** `geobase_distrital.gpkg`. Ningún notebook desde `00b` en adelante usa ya el shapefile crudo (`limite_distrital`) directamente.
4. **Estructura de datos:** `data/raw/` (crudo, pesado, ignorado en git) → `data/clean/staging/` (un archivo por fuente, sí versionado en git) → `data/clean/merged/` (panel unido final).
5. **Notebooks organizados en celdas separadas**: setup → funciones → descarga (celda aparte) → consolidar → validar → guardar. Así una descarga larga o que falla no hace perder el trabajo de consolidación.
6. **Earth Engine** (`00b` a `00f`): lotes de 40 distritos, geometría simplificada para fuentes de píxeles (SRTM, JRC, NDVI, ESA World Cover) pero **sin simplificar** para Open Buildings (vectores, filtro espacial exacto). `ee.Initialize(project="viirs-peru")` al inicio de cada notebook.

### Lecciones de rendimiento en Earth Engine (aplican a cualquier `reduceRegions` futuro)

- Cronometrar justo antes del `.getInfo()` real, no antes de construir el `ee.FeatureCollection` (es lazy).
- Ordenar los lotes por `geometry.hilbert_distance()` antes de partirlos — lotes geográficamente compactos evitan traer tiles de todo el país.
- `scale=30` en vez de la resolución nativa (10m) para agregados distritales: ~9x más rápido, precisión prácticamente idéntica a este nivel de agregación.
- Filtro de nubes más estricto (`< 20%`) y muestreo de meses representativos para colecciones temporales (Sentinel-2), en vez de los 12 meses completos.
- Un solo distrito amazónico gigante (Loreto, Ucayali, Madre de Dios) puede colgar un lote entero.

---

## 1. `00a_geobase.ipynb` — Terminado

Cruza el shapefile INEI 2025 (`Limite Distrital INEI 2025 CPV`) con la tabla censal de UBIGEO. Se identificaron y documentaron **5 discrepancias** de cruce (San Antonio-Moquegua y Alto Trujillo en el shapefile pero no en la tabla; Putumayo, Teniente Manuel Clavero y Santa María de Huachipa en la tabla pero no en el shapefile). Se excluyeron del análisis en vez de forzar el cruce.

- **Universo final: 1889 distritos.**
- **Columnas:** `UBIGEO`, `departamento`, `provincia`, `distrito`, `region`, `macroregion_inei`, `macroregion_minsa`, `capital`, `latitude`, `longitude`, `altitude`, `superficie`, `pob_densidad_2020`, `geometry`.
- Se dejaron fuera para `03_causal_model`: `indice_vulnerabilidad_alimentaria`, `idh_2019`, `pct_pobreza_total`, `pct_pobreza_extrema`.
- **Hallazgo de esta bitácora (no documentado antes):** `superficie` y `pob_densidad_2020` quedaron guardadas como **texto** en el `.gpkg` (no numérico), y **15 de los 1889 distritos** (ej. Ahuayro, Putis, Unión Progreso, Kumpirushiatro, Cielo Punco, Manitea, Unión Asháninka — mayoría selva/zonas remotas) tienen `capital`, `latitude`, `longitude`, `altitude`, `superficie` y `pob_densidad_2020` genuinamente vacíos en la fuente. No es un bug del pipeline, es un vacío del dato censal/geográfico de origen — hay que documentarlo en la pantalla de limitaciones.
- Salida: `data/clean/staging/geobase_distrital.gpkg`.

## 2. `00b_srtm.ipynb` — Terminado

Elevación media y pendiente media (SRTM 30m) por distrito. Nota de dominio: la altitud se conserva porque OMS/MINSA ajustan el punto de corte de hemoglobina según altitud — es insumo necesario para interpretar los tamizajes de anemia, no decorativo.

- Salida: `srtm_distrital.csv` (`ubigeo`, `elevacion_media`, `pendiente_media`).

## 3. `00c_jrc.ipynb` — Terminado

JRC Global Surface Water: % de agua permanente y estacional por distrito.

- Salida: `jrc_distrital.csv` (`ubigeo`, `pct_agua_permanente`, `pct_agua_estacional`). **1806 de 1889 distritos** — los 83 restantes no tuvieron agua detectada (se trata como 0%, no como dato faltante, al momento del merge).

## 4. `00d_ndvi_extraction.ipynb` — En proceso, no incorporado todavía al merge

Serie temporal Sentinel-2 (NDVI). Se colgaba de forma impredecible en lotes específicos (hasta 35-40 min). Causas corregidas: lotes no ordenados geográficamente, filtro de nubes muy permisivo (`<80%` → `<20%`), año completo en vez de muestreo bimestral (meses `[1,3,5,7,9,11]`, trade-off aceptado de precisión fenológica por velocidad). Dividido en una celda por año (2021-2025).

- **Pendiente:** correr una pasada completa limpia y confirmar que las optimizaciones evitan el cuelgue. **Este archivo (`sentinel2_ndvi_distrital_2021_2025.csv`) todavía no existe en `staging/` y por lo tanto no está en el panel final.**

## 5. `00e_building_density_extraction.ipynb` — Terminado

Google Open Buildings V3: conteo de edificaciones, área construida, confianza media, densidad por km². Sin simplificar geometría (un borde de distrito corrido puede perder o duplicar edificaciones cerca del límite).

- Salida: `open_buildings_distrital.csv` (`ubigeo`, `n_edificios`, `area_construida_m2`, `confianza_media`, `area_distrito_km2`, `densidad_edificios_km2`).

## 6. `00f_esa_world_cover.ipynb` — Terminado

ESA WorldCover 2021: % cultivo, construido, suelo desnudo, agua visible. Mismo síntoma de cuelgues que NDVI; causa adicional identificada: `reduceRegions` corría a `scale=10` (resolución nativa), carísimo en distritos amazónicos. Fix: `scale=30`.

- Salida: `esa_worldcover_distrital_2021.csv` (`ubigeo`, `pct_cultivo`, `pct_construido`, `pct_desnudo`, `pct_agua_visible`).

## 7. `00g_renamu.ipynb` — Terminado (con una corrección pendiente de aplicar en el merge, ver §10)

Fuente: RENAMU (INEI), encuesta anual a municipalidades. Sirve como **variable de control**, no de contexto satelital: evita que el modelo confunda "el gasto no rinde por el territorio" con "el gasto no rinde por mala gestión municipal".

- **Panel arranca en 2021** (no 2020): el módulo de anemia recién aparece en 2021, y desde ese año el formato está estandarizado.
- **Hallazgo importante — corrección de código:** `programa_anemia` estaba mal mapeado a `P68_7` (que en realidad es "control de ITS y VIH/SIDA"). Se corrigió a `P68_10`, código correcto de "Prevención y reducción de la anemia". **Verificado directamente contra el diccionario oficial en esta sesión** (`Diccionario_Anexo01.pdf`, pregunta 59, Módulo V - Salud):
  > *"En el año 2020, ¿La municipalidad implementó programas de control y prevención de la salud en coordinación con el MINSA en: Prevención y reducción de la anemia"* — códigos `0: Pase`, `10: Sí`.
- **Variables extraídas** (fuente verificada en el diccionario oficial):

  | Variable | Código pregunta | Definición oficial | Corrección de año necesaria |
  |---|---|---|---|
  | `personal_total` | P19D_T | "Total personal / 31 de diciembre 2020" (retrospectivo) | Año real = Año_encuesta − 1 |
  | `programa_anemia` | P68_10 | Ver cita arriba | Año real = Año_encuesta − 1 |
  | `centro_salud_municipal` | P66_2 | "¿En el Distrito funcionan establecimientos de salud administrados por la Municipalidad: Centro de salud?" — 1: Sí / 2: No (tiempo presente) | Sin corrección: año real = Año_encuesta |

- **Decisión de diseño:** una sola tabla panel (no tres separadas), con un único `Año` = año de encuesta. La corrección de desfase (`Año − 1` para las dos primeras variables) queda documentada para aplicarse **en el notebook donde se construya la tabla maestra**, no en `00g`.
- Se validaron los `ubigeo` contra `geobase_distrital.gpkg`, excluyendo los que no calzan.
- **Pendiente sin confirmar:** que el código `10 = Sí` de `programa_anemia` se mantiene igual en los diccionarios 2022-2025 (no se hizo `value_counts()` año por año todavía).
- Salida: `renamu_distrital_2021_2024.csv` (`ubigeo`, `Año`, `personal_total`, `programa_anemia`, `centro_salud_municipal`).

## 8. `00h_sien_reunis.ipynb` — Terminado, con una validación pendiente

Fuente: SIEN/HIS-MINSA vía portal REUNIS. Sin descarga directa en CSV (portal de tableros); se trabajó con `Trama_Base_Anemia.xlsx` (355,876 filas individuales de tamizaje), obtenido por fuera del flujo normal de descarga.

- **Bug de ruta relativa** (mismo patrón que 00a-00g): corregido con el bloque `find_project_root()`.
- **Bug de mayúsculas:** la columna viene como `Ubigeo` en el Excel crudo, no `ubigeo`; causaba `KeyError`. Se corrigió el `groupby` y se renombra a `ubigeo` (minúscula) al final para que combine con la convención del resto del proyecto.
- **Filtro aplicado:** `Edad == 1` (menores de 3 años), confirmado contra el tablero oficial.
- **Agregación:** por `ubigeo` + `Año` → `ninos_evaluados` (suma de `Evaluados`), `ninos_con_anemia` (suma de `Anemia`), `ninos_sin_anemia` (suma de `Normal`), `prevalencia_anemia = ninos_con_anemia / ninos_evaluados`.
- Rango real de datos: **2020 a 2026** (verificado: `sorted(sien["Año"].unique())` = `[2020, 2021, 2022, 2023, 2024, 2025, 2026]`).
- Salida verificada: `sien_reunis_distrital_2020_2026.csv`, shape `(13029, 9)`.
- **⚠️ Pendiente NO resuelto (confirmado al releer el notebook en esta sesión):** a diferencia de RENAMU y SIAF, **este notebook todavía no valida `ubigeo` contra `geobase_distrital.gpkg`**. Esto es la causa directa de que 2 ubigeos ajenos al universo de 1889 distritos (`130112`, `180107`) hayan entrado al panel final sin ser detectados — ver §10.
- **Discusión metodológica documentada:** la base de anemia está filtrada a menores de 3 años, pero el contexto territorial satelital y RENAMU son a nivel distrital agregado. Se concluyó que el riesgo de sesgo de agregación ecológica es tolerable a nivel de caserío rural (composición demográfica uniforme dentro de un mismo centro poblado), pero debe declararse en la pantalla de limitaciones. El **gasto SIAF sí debería normalizarse por población infantil evaluada** en vez de dejarse en soles absolutos — pendiente, sugerido traer el Padrón Nominal de REUNIS.

## 9. `00i_siaf_gasto_devengado.ipynb` — Terminado (esta bitácora se escribe por primera vez aquí; el notebook no tenía bitácora previa, pero sí trae su propia documentación interna extensa)

Fuente: MEF, "Presupuesto y Ejecución de Gasto — Devengado Mensual" (`datosabiertos.mef.gob.pe`). Un CSV por año, 2021-2025 (rango elegido por coincidir con la cobertura de SIEN).

- **Fase contable usada: Devengado** (el bien/servicio ya fue recibido y la obligación de pago reconocida — el estándar para "cuánto se gastó realmente", no lo planeado ni lo pagado).
- **Problema de granularidad temporal:** las columnas mensuales (`MONTO_DEVENGADO_ENERO`...`DICIEMBRE`) solo vienen pobladas en **2025**; en 2021-2024 vienen en cero y el único monto confiable es `MONTO_DEVENGADO_ANUAL`. Se normalizó a una sola columna `monto_devengado_anual`: directo para 2021-2024, suma de los 12 meses para 2025.
- **Construcción del UBIGEO:** `DEPARTAMENTO_EJECUTORA + PROVINCIA_EJECUTORA + DISTRITO_EJECUTORA` (3 códigos de 2 dígitos → 6 dígitos).
- **⚠️ Limitación estructural importante, documentada explícitamente en el notebook:** este UBIGEO identifica **dónde está registrada la unidad ejecutora del gasto**, no necesariamente el distrito donde se presta el servicio (ej. una unidad ejecutora regional de salud puede estar en la capital de provincia y administrar gasto que se ejecuta en distritos rurales alrededor). Se evaluó usar `DEPARTAMENTO_META` (nivel de la actividad específica) como alternativa, pero solo llega a nivel departamento, no distrito. **Decisión:** se usa `DISTRITO_EJECUTORA` como proxy, declarado como limitación conocida.
- **Validación contra INEI:** el ubigeo construido cruzó correctamente en **1891 de 1892 casos (99.9%)**. El único que no cruzó: `160405` — **Santa Rosa de Loreto** (provincia Mariscal Ramón Castilla, Loreto), distrito creado el 3 de julio de 2025 (Ley N° 32403), separado de Yavarí; el shapefile INEI de referencia es anterior a esa fecha. **Se excluyó del dataset** (67 filas, S/ 402,358.70 en total 2021-2025, todos los programas — monto marginal frente al total nacional; tampoco tendría contexto satelital propio para el modelo causal).
- **Variables construidas:**
  - `gasto_total` = suma de `monto_devengado_anual` de **todos** los programas presupuestales, por `ubigeo` + `ANO_EJE`.
  - `gasto_anemia_pan` = mismo cálculo, filtrado solo a `PROGRAMA_PPTO == '0001'` (Programa Articulado Nutricional). Si un distrito no ejecutó nada en PAN ese año, se rellena con `0` (no se deja vacío).
- **Verificado contra el diccionario oficial** (`Gasto_Devengado_Diccionario.csv`, leído en esta sesión): confirma definiciones exactas de `ANO_EJE`, `PROGRAMA_PPTO`, `MONTO_DEVENGADO_*`, y que `TIPO_TRANSACCION = 2` siempre corresponde a Gasto (no Ingreso) en este reporte.
- **3 combinaciones ubigeo-año sin ninguna fila en SIAF:** `(2021, 180107)`, `(2021, 130112)`, `(2022, 130112)` — no se investigó la causa (probablemente sin ejecución presupuestal reportada ese año); quedan como `NaN` tras el merge, no como error.
- Cobertura final por año: 2021 (1889 distritos), 2022 (1890), 2023 (1891), 2024 (1891), 2025 (1891) — después de excluir `160405`.
- Salida verificada: `siaf_gasto_devengado_distrital_2021_2025.csv`, **9452 filas**.
- **Pendiente explícito del propio notebook:** confirmar la lista final de `PROGRAMA_PPTO` a incluir en `gasto_anemia` (hoy solo PAN 0001; el documento maestro también menciona salud materno-neonatal, saneamiento rural, Cuna Más, Qali Warma, JUNTOS e incentivos municipales como programas con incidencia en anemia, todavía no incorporados al filtro).

---

## 10. El merge — `02_anemia_and_spending_models/00a_mergue_database.ipynb`

**⚠️ Hallazgo crítico de esta sesión: el archivo del notebook está vacío en disco (0 bytes).** Las celdas de normalización y merge se ejecutaron interactivamente durante esta conversación y sí produjeron el archivo final (`panel_distrital_final.csv`, generado hace pocos minutos), pero el notebook nunca se guardó (`Ctrl+S` / `File > Save`). **Acción pendiente inmediata: volver a pegar las celdas y guardar el notebook**, o el trabajo de esta sesión se pierde en la próxima vez que se abra VS Code.

### Metodología aplicada

1. Carga de las 8 tablas de `staging/` (7 CSV + 1 GPKG).
2. Normalización por archivo: `ubigeo` → string de 6 dígitos con cero a la izquierda (crítico: varias tablas lo traían como `int64`, perdiendo el cero de los departamentos 01-09); columnas de año (`Año`, `ANO_EJE`) → renombradas a `anio`.
3. Separación en tablas **estáticas** (geobase, esa_worldcover, open_buildings, srtm, jrc — una fila por distrito) y **panel** (renamu, siaf, sien_reunis — distrito × año).
4. `jrc`: los 83 distritos sin dato se rellenaron con `0` explícitamente (no `NaN`) al momento del merge — decisión de que "sin agua detectada" es distinto de "sin dato".
5. Base estática: `geobase` como tabla maestra, `merge(..., how="left")` sucesivo del resto.
6. Base panel: `sien_reunis` como base, `merge(..., how="outer")` con `siaf` y `renamu` por `["ubigeo", "anio"]`, para no perder ningún año que alguna fuente sí cubra y otra no.
7. Merge final: panel `merge` estática por `ubigeo` (`how="left"`), broadcast del contexto territorial a cada fila del panel.
8. Guardado en `data/clean/merged/panel_distrital_final.csv`.

### Validación real, ejecutada sobre el archivo actual en disco en esta sesión

- **Shape:** `(13148, 36)`.
- **Ubigeos únicos: 1891** — **2 más que el universo de geobase (1889)**: `130112` y `180107`. Estos dos ubigeos vienen de `sien_reunis` y/o `renamu` (que **no validan contra geobase**, a diferencia de SIAF que sí lo hizo) y por lo tanto no tienen ninguna variable de contexto territorial — quedan con **9 filas totales en `NaN`** en todas las columnas estáticas (departamento, coordenadas, cobertura de suelo, edificaciones, elevación, agua). Recomendación: aplicarles el mismo tratamiento que se le dio a `160405` en SIAF (investigar si son distritos nuevos y decidir exclusión vs. reasignación al distrito de origen).
- **0 duplicados** en la clave `ubigeo + anio`.
- **Nulos por variable, explicados:**

  | Variable(s) | Nulos | Causa |
  |---|---|---|
  | `ninos_evaluados/con_anemia/sin_anemia` | 119 | Filas agregadas por el `outer join` de SIAF/RENAMU para combinaciones ubigeo-año que SIEN no reporta |
  | `prevalencia_anemia` | 161 | Los 119 anteriores + casos con `ninos_evaluados = 0` (división por cero) |
  | `gasto_total`, `gasto_anemia_pan` | 3696 | Años 2020, 2026 fuera de la cobertura real de SIAF (2021-2025) |
  | `personal_total` | 5812 | Años 2020, 2025, 2026 fuera de la cobertura real de RENAMU (2021-2024) + algunos huecos dentro del panel |
  | `programa_anemia`, `centro_salud_municipal` | 5622 | Mismo motivo |
  | `departamento`...`macroregion_minsa` | 9 | Los 2 ubigeos sin match en geobase (`130112`, `180107`) |
  | `capital`, `latitude`, `longitude`, `altitude` | 97 | 9 de los `NaN` anteriores + **15 distritos que ya tenían este dato vacío en el propio `geobase_distrital.gpkg` de origen** (ver §1), replicados por cada año en que aparecen en el panel |
  | `superficie`, `pob_densidad_2020` | 125 | Mismo motivo que la fila anterior. La conversión de texto a número (`str` → `float`) se hizo sin errores de parseo — los nulos son 100% del dato de origen, no de la conversión |
  | `pct_agua_permanente`, `pct_agua_estacional` | 9 | Solo los 2 ubigeos sin match en geobase — el `fillna(0)` de los 83 distritos sin agua detectada sí funcionó como se diseñó |
  | resto de columnas estáticas (`esa_worldcover`, `open_buildings`, `srtm`) | 9 | Solo los 2 ubigeos sin match en geobase |

### ⚠️ Pendiente crítico no aplicado todavía

**La corrección de año retrospectivo de RENAMU (§7) no se aplicó en este merge.** `personal_total` y `programa_anemia` describen en realidad el año anterior al que aparece en la fila (`anio - 1`), pero el merge actual los dejó pegados directamente al `Año` de la encuesta sin corregir. Esto significa que, tal como está hoy el archivo, la fila `anio = 2021` de `personal_total`/`programa_anemia` describe realmente diciembre de 2020, pero se está comparando contra el gasto y la anemia de 2021 — un desfase de un año que hay que corregir antes de usar estas columnas en el modelo causal.

---

## 11. Lista consolidada de pendientes (todas las fuentes)

1. **Guardar `00a_mergue_database.ipynb`** — está vacío en disco pese a haber producido el output final.
2. **Aplicar la corrección de año de RENAMU** (`personal_total`, `programa_anemia` → `anio - 1`) antes de usar el panel en el modelo causal.
3. **Decidir el tratamiento de `130112` y `180107`** (no están en geobase, 9 filas del panel final sin contexto territorial) — mismo criterio que se usó con `160405` en SIAF.
4. **Agregar validación de `ubigeo` contra `geobase_distrital.gpkg` en `00h_sien_reunis.ipynb`** (es la causa raíz del punto 3).
5. **Confirmar `value_counts()` año por año** de que el código `10 = Sí` de `programa_anemia` se mantiene igual en los diccionarios RENAMU 2022-2025.
6. **Correr `00d_ndvi_extraction.ipynb` y `00f_esa_world_cover.ipynb`** hasta confirmar que las optimizaciones evitan cuelgues, y en el caso de NDVI, generar el CSV final (todavía no existe, no está en el panel).
7. **Normalizar `gasto_total`/`gasto_anemia_pan` por población infantil evaluada** (per cápita) en vez de dejarlos en soles absolutos — pendiente sugerido desde `00h`, requiere el Padrón Nominal de REUNIS.
8. **Ampliar el filtro de `PROGRAMA_PPTO`** más allá de PAN (0001) a los demás programas con incidencia en anemia mencionados en el documento maestro (salud materno-neonatal, saneamiento rural, Cuna Más, Qali Warma, JUNTOS, incentivos municipales).
9. **Documentar en la pantalla de limitaciones de la app:** los 15 distritos sin coordenadas/superficie de origen, el UBIGEO de SIAF como proxy de unidad ejecutora (no distrito de intervención real), y el sesgo de agregación ecológica entre anemia (menores de 3 años) y contexto territorial (distrito completo).
10. **Incorporar ENDES** (ya está en `data/raw/ENDES_peso_talla_anemia/`, con sus diccionarios REC44/RECH5/RECH6) para la corrección de sesgo de selección del tamizaje — todavía no tocado en ningún notebook.
