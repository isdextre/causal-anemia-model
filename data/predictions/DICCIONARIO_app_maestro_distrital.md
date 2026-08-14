# Diccionario de datos — `app_maestro_distrital.csv`

Este es el único archivo que la app necesita para pintar los 3 mapas y el panel de detalle por distrito. Une todo lo que salió de los notebooks de modelo causal (`01_anemia_model`, `01_spending_model`, `02_causal_forest`, `02_contrafractual`) en una sola tabla, una fila por distrito.

**1,889 filas = todos los distritos del Perú.** Ningún distrito se excluyó de este archivo — donde falta un dato, la columna `dato_..._disponible` correspondiente dice `False` y el valor va vacío. La app debe mostrar esos casos como "dato insuficiente", nunca como cero.

## Columnas

| Columna | Qué es | Cómo usarla en la app |
|---|---|---|
| `ubigeo` | Código único del distrito (INEI) | Llave para cruzar con mapas/shapefiles |
| `distrito`, `provincia`, `departamento` | Nombres | Etiquetas, filtros, buscador |
| `prevalencia_anemia_actual` | % de niños con anemia, del año más reciente con dato real disponible para ese distrito (entre 2021-2025) | **Mapa 1 — "dónde duele"**. Es un dato observado (SIEN/MINSA), no una predicción |
| `anio_referencia_anemia` | De qué año es el dato de arriba | Mostrar como nota ("dato de 2023", por ejemplo) — no todos los distritos tienen el mismo año |
| `dato_anemia_disponible` | `True`/`False` | Si es `False`, ese distrito no tiene ningún año con tamizaje registrado — mostrar "sin dato", no pintar como 0% |
| `gasto_pan_percapita_actual` | Gasto del Programa Articulado Nutricional, en soles por niño evaluado, año más reciente disponible | Dato de contexto, no es lo que se usó internamente para entrenar (eso fue el log) |
| `anio_referencia_gasto` | De qué año es el gasto de arriba | Igual que con anemia, puede variar por distrito |
| `dato_gasto_disponible` | `True`/`False` | Si es `False`, no hay gasto PAN confiable registrado (o no se ejecutó, o el dato es un outlier administrativo excluido) |
| `indice_priorizacion_tau` | El número central del modelo causal — qué tanto "rinde" el gasto en ese distrito | **Mapa 2 — "dónde rinde el gasto"**. **Importante:** NO decir "el gasto reduce la anemia en X" — es un índice de priorización relativo entre distritos, no un efecto causal probado. Ver limitación abajo |
| `tau_intervalo_inferior`, `tau_intervalo_superior` | Rango de confianza al 95% del número de arriba | Mostrar como rango en el tooltip del mapa, no solo el punto central |
| `tau_es_confiable` | `True`/`False` — si el intervalo de confianza no cruza cero | Usar para diferenciar visualmente los distritos donde el modelo confía del resto (ej. opacidad más baja si es `False`) |
| `dato_priorizacion_disponible` | `True`/`False` | Si es `False` (13 distritos), no hubo suficiente dato de anemia y/o gasto para calcular τ ahí — mostrar como "sin dato", nunca inventar un valor |
| `cuello_de_botella_dominante` | Cuál de las 3 variables simuladas (agua, dispersión, urbanización) mejoraría más el τ de ese distrito si se resolviera. Puede decir `"ninguno (ya en percentil 75+)"` o `"sin dato"` | **Panel de detalle**. Es el titular del cuadro contrafactual: "el freno principal aquí es ___" |
| `delta_tau_agua_segura`, `delta_tau_dispersion`, `delta_tau_urbanizacion` | Cuánto subiría τ si esa variable específica mejorara al nivel de un distrito bien servido (percentil 75 nacional) | **Simulador contrafactual** — graficar como 3 barras por distrito, NUNCA como imagen generada (ver limitación abajo) |

## Limitaciones que la pantalla de metodología debe declarar

- **El signo del efecto salió positivo:** más gasto residual va asociado a más anemia residual, no menos. Esto refleja que el Estado dirige el gasto hacia donde ya hay más anemia (focalización), y el modelo no logra separar del todo esa focalización sin un instrumento causal validado. Por eso `indice_priorizacion_tau` se comunica como índice relativo, no como "cuánta anemia se evita por sol invertido".
- Los cuellos de botella originalmente planeados eran 4 (agua, dispersión, vía, cobertura de salud). Solo se pudieron simular 3 — "vía de acceso" y "cobertura de salud" no existen como variables en los datos actuales.
- El contrafactual es estrictamente numérico por decisión de diseño — nunca generar una imagen o render de "cómo se vería" un distrito con mejor acceso.
- `prevalencia_anemia_actual` viene de registro administrativo (SIEN), refleja quién llegó a tamizarse, no un censo — puede subestimar la anemia real en distritos con poco acceso a salud.
