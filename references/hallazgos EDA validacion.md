# Hallazgos de validación EDA — `panel_distrital_final.csv`

Validación programática ejecutada directamente sobre los archivos en disco del repo (`data/clean/merged/panel_distrital_final.csv`, los 7 staging CSV, `geobase_distrital.gpkg`, y las 4 bases crudas RENAMU 2021-2024), cruzando contra lo documentado en el diccionario de datos y la bitácora `00a-00i`.

## Confirmado correcto (sin hallazgos)

- Shape `(13148, 36)`, nulos por columna: **coinciden exactamente** con lo documentado en el diccionario, columna por columna.
- `ubigeo`: 100% de 6 dígitos, cero a la izquierda preservado.
- `0` duplicados en `ubigeo + anio`.
- `prevalencia_anemia`: rango correcto [0,1], sin valores fuera de rango.
- `ninos_evaluados = ninos_con_anemia + ninos_sin_anemia` en el 100% de las filas no nulas.
- `pct_*` (cultivo, construido, desnudo, agua visible/permanente/estacional): todos dentro de [0,1].
- `gasto_total` y `gasto_anemia_pan`: sin negativos, `gasto_anemia_pan` nunca mayor que `gasto_total`.
- Nombres de columnas: idénticos entre staging y merge final — no hay renombres accidentales en esa etapa.

## Hallazgo 1 (crítico) — `programa_anemia` y `centro_salud_municipal` decodificados mal en años con marcador `#¡NULO!`

Las bases crudas de RENAMU usan el string literal `#¡NULO!` (marcador de Excel) para "no aplica / sin respuesta" en ciertas preguntas y años:

- **`P66_2` (→ `centro_salud_municipal`) en 2022**: de 1874 filas, **1368 son `#¡NULO!`**, 338 son `'2'` (No), 168 son `'1'` (Sí).
- **`P68_10` (→ `programa_anemia`) en 2023**: de 1891 filas, **563 son `#¡NULO!`**, 490 son `'0'` (No), 838 son `'10'` (Sí).

En el archivo staging (`renamu_distrital_2021_2024.csv`), estos casos **NO quedaron como nulos** — quedaron codificados como `0` ("No"):

- `centro_salud_municipal` 2022: `0 = 1706` (= 1368 NULO + 338 No reales), `1 = 168`.
- `programa_anemia` 2023: `0 = 1051` (= 563 NULO + 490 No reales), `1 = 838`.

Es decir, en 2022 el 73% de los distritos quedaron marcados como "no tiene centro de salud municipal" cuando en realidad no respondieron la pregunta, y en 2023 el 30% quedaron marcados como "no implementó programa de anemia" sin haber respondido. Esto sesga artificialmente estas dos variables de control hacia "No" en esos años específicos.

**Contraste:** `personal_total` (`P19D_T`) sí maneja bien el mismo marcador en 2023 (80 casos) y 2024 (110 casos) — quedan como `NaN`, no como `0`. El bug es específico de cómo se procesaron `P68_10`/`P66_2`, no un problema general del notebook.

**Acción sugerida:** re-procesar `00g_renamu.ipynb` mapeando explícitamente `#¡NULO!` → `NaN` antes de castear a numérico, para `P68_10` y `P66_2` en todos los años (no solo donde ya se ve el síntoma — vale la pena revisar si aparece en 2021/2024 con otro nombre de marcador).

## Hallazgo 2 (importante) — `region` no contiene costa/sierra/selva, contiene el nombre del departamento

El diccionario describe `region` como *"Región geográfica (costa/sierra/selva u homóloga)"*. En la práctica, `geobase_distrital.gpkg` (fuente original, no un problema del merge) tiene `region` como una copia literal de `departamento` (ej. fila `010101`: `departamento = AMAZONAS`, `region = AMAZONAS`). Son 26 valores únicos (los 24 departamentos + Lima Provincia/Lima Región separados), no 3 categorías naturales. No es un bug de mezcla de datos — el propio `00a_geobase.ipynb` generó la columna así — pero la documentación actual promete algo que la columna no tiene. Si el modelo o la app necesitan costa/sierra/selva real, hay que construirla aparte (hay tablas públicas INEI de clasificación natural por distrito) o corregir la documentación para no prometer una categoría que no existe.

## Hallazgo 3 (importante) — 2 distritos con gasto NO marginal pierden todo su contexto territorial en el merge

La bitácora documenta `130112` (Alto Trujillo) y `180107` (San Antonio, Moquegua) como "sin match en geobase" y los compara implícitamente con el caso de `160405` (Santa Rosa de Loreto, excluido de SIAF por ser marginal: S/402k). Pero al revisar `sien_reunis_distrital_2020_2026.csv`, estos dos ubigeos **sí tienen nombre de departamento/provincia/distrito** (vienen con esa info desde el Excel de MINSA: `130112` = La Libertad/Trujillo/Alto Trujillo, `180107` = Moquegua/Mariscal Nieto/San Antonio), y su gasto acumulado en el panel **no es marginal en absoluto**:

- `130112`: S/ 33.4 millones acumulados, 5,771 niños evaluados.
- `180107`: **S/ 601 millones** acumulados, 1,288 niños evaluados.

Además, durante el merge final, las columnas `departamento`/`provincia`/`distrito` que sí traía `sien_reunis` para estos dos ubigeos **se pierden** (quedan `NaN` en el panel final) porque el merge con la tabla estática de `geobase` las sobrescribe. Con 601 millones de soles en juego, tratar `180107` igual que el caso marginal de `160405` (excluirlo sin más) descartaría una cantidad de gasto grande del análisis. Vale la pena investigar si `180107`/`130112` corresponden a distritos que cambiaron de código o de límites después del corte del shapefile INEI 2025, y si se les puede asignar geometría/contexto territorial manualmente en vez de dejarlos huérfanos.

## Confirmado — pendientes ya documentados, sin novedad

Se confirmó en código (no solo se tomó la palabra de la bitácora) que siguen pendientes: el desfase de año de RENAMU (`personal_total`/`programa_anemia` sin corregir a `anio - 1`), el notebook de merge vacío en disco, y que el código `P68_10` (10=Sí / 0=No) sí se mantiene estable como código en los diccionarios 2021-2024 (aparte del bug de `#¡NULO!` de Hallazgo 1).