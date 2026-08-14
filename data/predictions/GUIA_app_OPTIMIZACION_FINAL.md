# Guía para el programador de la app — `OPTIMIZACION_FINAL.csv`

Este archivo alimenta el **Mapa 3** de la app ("reasignación propuesta"). No necesitas entender el modelo causal para usarlo — esta guía te dice, columna por columna, qué es y qué construir con ella.

**1,889 filas = todos los distritos del Perú.** No falta ninguno.

## Qué es este archivo, en una frase

Es una simulación de "¿qué pasaría si movemos el mismo presupuesto de nutrición infantil (PAN) entre distritos, dándole más a los que tienen mejor índice de priorización y menos a los que tienen peor, sin dejar a nadie con una pérdida mayor al 20%?". No cambia el gasto real de nadie — es una recomendación, no un hecho ya ejecutado.

## Columna por columna

**`ubigeo`** — código único del distrito. Úsalo para cruzar con el shapefile/geojson del mapa, igual que en `app_maestro_distrital.csv`.

**`distrito`, `provincia`, `departamento`** — nombres, para el buscador y las etiquetas.

**`gasto_actual_soles`** — cuánto gastaba el distrito antes de la propuesta, en soles. Úsalo como el número de "ANTES" en cualquier comparación.

**`anio_referencia_presupuesto_base`** — de qué año es ese gasto actual (2021 o 2022 — no uses años más recientes, hay un problema de datos ahí que ya se le avisó a la analista, no es relevante para ti). Muéstralo como nota pequeña ("base: 2022").

**`indice_priorizacion_tau`** — qué tan fuerte es el patrón entre gasto y anemia en ese distrito, según el modelo. Mientras más alto, más "prioridad" tiene el distrito en esta propuesta. **No lo muestres como "porcentaje de anemia evitada" ni nada parecido — es un índice relativo, no una cifra de impacto.** Si quieres mostrarlo, ponlo como una barra o un número simple con la etiqueta "índice de priorización", sin unidades.

**`tau_es_confiable`** — `True`/`False`. Si es `False`, el modelo no está seguro de ese índice para ese distrito — bájale la opacidad en el mapa o ponle un ícono de "advertencia", no lo trates igual que uno confiable.

**`incluido_en_optimizacion`** — `True`/`False`. Los 13 distritos con `False` no tienen dato suficiente y se quedaron con su presupuesto sin cambios a propósito, no por error. Muéstralos como "sin cambio propuesto (dato insuficiente)", nunca escondidos ni como si tuvieran cambio cero por decisión del modelo.

**`gasto_propuesto_soles`** — el número de "DESPUÉS" — cuánto se propone que gaste el distrito con la reasignación. Compáralo contra `gasto_actual_soles` en un antes/después (dos barras, o una flecha).

**`cambio_soles`** — la diferencia en soles (`gasto_propuesto_soles − gasto_actual_soles`). Positivo = gana presupuesto, negativo = pierde. **Esta es la columna más importante para el color del mapa** — usa una escala de dos colores (ej. verde para positivo, rojo para negativo), no una escala de un solo color.

**`cambio_porcentual`** — el cambio en porcentaje. **Cuidado con esta columna:** para distritos que casi no gastaban nada antes (por ejemplo S/8), un aumento chico en soles se ve como un porcentaje gigante (hay casos de +4,000%). No la uses para el color del mapa ni la muestres como titular — solo como dato secundario en el detalle del distrito, y si la muestras, ponle un límite visual (por ejemplo, "más de +200%" en vez del número exacto cuando sea extremo).

## Un patrón que vas a notar y no es un error

Muchos distritos pequeños van a tener exactamente el mismo `cambio_soles` (~S/104,239). No es un bug — es el tope máximo de aumento que el modelo le puso a todos por igual, y varios lo alcanzaron justo en ese límite. Es normal, no hace falta que lo arregles ni preguntes por qué se repite.

## Sugerencia de cómo armar el Mapa 3

1. Colorea cada distrito por `cambio_soles` (rojo = pierde, blanco/gris = casi sin cambio, verde = gana).
2. En el tooltip al pasar el mouse: nombre del distrito, `gasto_actual_soles` → `gasto_propuesto_soles`, y el `cambio_soles` con signo (+/-).
3. Al hacer click en un distrito, en el panel de detalle muestra las dos barras (actual vs. propuesto) una al lado de la otra, más el `indice_priorizacion_tau` como referencia de por qué se le movió el presupuesto.
4. Si `incluido_en_optimizacion` es `False`, no lo coloreies como "sin cambio" (blanco/gris igual que uno neutral) — dale un patrón distinto (rayado, o gris apagado) con la etiqueta "sin dato suficiente para proponer cambio".

## Lo que NUNCA debe decir la app con este archivo

No digas "esta reasignación evita X casos de anemia" — el archivo no calcula eso, y decirlo sería inventar una cifra que el modelo no respalda (ver la pantalla de metodología para el porqué). Lo correcto es "esta es una propuesta de reasignación basada en el índice de priorización del modelo, sujeta a las limitaciones declaradas en la metodología".
