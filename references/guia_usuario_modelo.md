# Guía de Usuario — Predictor de Alto Riesgo de Anemia Distrital

## ¿Qué hace el modelo?

El modelo clasifica si un distrito peruano tendrá **alto riesgo de anemia infantil** en el año siguiente, dado su perfil actual y los valores de política que el usuario puede ajustar. Devuelve:

- **Clasificación**: ALTO RIESGO / BAJO RIESGO
- **Probabilidad**: entre 0 % y 100 % de caer en alto riesgo
- **Año predicho**: último año con datos + 1

El umbral de clasificación fue optimizado sobre el panel distrital 2017-2022 usando un Random Forest con validación cruzada temporal.

---

## Cómo ejecutar la app

### Requisitos

```bash
pip install streamlit scikit-learn pandas numpy
```

### Lanzar

Desde la raíz del repositorio:

```bash
streamlit run app/streamlit_app.py
```

Se abrirá el navegador en `http://localhost:8501`.

---

## Interfaz paso a paso

### 1. Seleccionar distrito

Usa el desplegable **"Distrito"** para elegir cualquiera de los ~1800 distritos del panel. Puedes escribir para filtrar.

Al seleccionar un distrito, los sliders se inicializan automáticamente con los valores reales más recientes de ese distrito.

### 2. Ajustar variables de política

Hay dos sliders que representan las variables de intervención:

| Variable | Descripción | Unidad |
|---|---|---|
| `personal_total` | Trabajadores de salud activos en el distrito | personas |
| `gasto_total` | Presupuesto ejecutado en salud | soles (S/) |

Los rangos de los sliders van de 0 al percentil 95 del panel, para evitar valores irreales.

> **Tip:** Mueve los sliders para simular escenarios de política: ¿qué pasa si duplicas el personal? ¿si aumentas el gasto en 50 %?

### 3. Leer el resultado

La predicción se actualiza en tiempo real. El bloque de resultados muestra:

- **Clasificación**: etiqueta binaria del riesgo
- **Probabilidad**: confianza del modelo en esa clasificación
- **Año predicho**: el año al que corresponde la predicción

Debajo aparece información contextual del distrito (departamento, provincia, altitud, macrorregión, prevalencia histórica).

---

## Artefacto del modelo

El archivo `outputs/model_artifacts.pkl` contiene todos los objetos necesarios para reproducir predicciones:

| Clave | Contenido |
|---|---|
| `model` | `RandomForestClassifier` entrenado |
| `encoder` | `OrdinalEncoder` para variables categóricas |
| `imputer` | `SimpleImputer` (mediana) para variables numéricas |
| `features` | Lista ordenada de features de entrada |
| `cat_cols` | Nombres de columnas categóricas |
| `num_cols` | Nombres de columnas numéricas |
| `threshold` | Umbral óptimo de clasificación (float) |
| `latest` | DataFrame con el último registro disponible por distrito |
| `umbral_anemia` | Umbral de prevalencia para definir "alto riesgo" |

### Usar el modelo en Python

```python
import pickle
import pandas as pd

with open("outputs/model_artifacts.pkl", "rb") as f:
    art = pickle.load(f)

model    = art["model"]
encoder  = art["encoder"]
imputer  = art["imputer"]
features = art["features"]
cat_cols = art["cat_cols"]
num_cols = art["num_cols"]

# Construir un DataFrame con las features del distrito de interés
X = pd.DataFrame([fila_distrito[features]])
X[cat_cols] = encoder.transform(X[cat_cols])
X[num_cols] = imputer.transform(X[num_cols])

prob  = model.predict_proba(X)[0, 1]
label = "ALTO RIESGO" if prob >= art["threshold"] else "BAJO RIESGO"
print(f"{label} — probabilidad: {prob:.1%}")
```

---

## Variables del modelo

El modelo usa las siguientes features (ver `data_dictionary_panel_distrital_final.md` para definiciones completas):

- Variables de **oferta sanitaria**: personal de salud, establecimientos, gasto ejecutado
- Variables **geográficas**: altitud, macrorregión INEI
- Variables de **contexto distrital**: pobreza, ruralidad, acceso a agua/desagüe
- Variables **temporales**: año del registro (tendencia)

Las dos variables de política ajustables en la app (`personal_total`, `gasto_total`) son las de mayor importancia en el modelo según permutation importance.

---

## Notas de uso

- Los datos base provienen del panel 2017-2022. Distritos sin datos recientes usan el último año disponible.
- El modelo **no predice prevalencia exacta**, solo clasifica riesgo binario.
- Para análisis por cluster de distritos, ver `outputs/clusters_distritales.csv` y el notebook `04_graph_clustering`.
