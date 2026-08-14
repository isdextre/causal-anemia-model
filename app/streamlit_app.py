import pickle
import numpy as np
import pandas as pd
import streamlit as st

# ── Cargar artefactos ────────────────────────────────────────────────────────
@st.cache_resource
def load_artifacts():
    with open("outputs/model_artifacts.pkl", "rb") as f:
        return pickle.load(f)

art = load_artifacts()

model     = art["model"]
encoder   = art["encoder"]
imputer   = art["imputer"]
features  = art["features"]
cat_cols  = art["cat_cols"]
num_cols  = art["num_cols"]
threshold = art["threshold"]
latest    = art["latest"]
UMBRAL    = art["umbral_anemia"]

latest      = latest.sort_values("nombre")
nombre_list = latest["nombre"].tolist()
ubigeo_map  = dict(zip(latest["nombre"], latest["ubigeo"]))
distrito_data = latest.set_index("ubigeo")

PERSONAL_MAX = int(latest["personal_total"].quantile(0.95))
GASTO_MAX    = int(latest["gasto_total"].quantile(0.95))


# ── Prediccion ───────────────────────────────────────────────────────────────
def predecir(nombre_distrito, personal_total, gasto_total):
    ubigeo = ubigeo_map.get(nombre_distrito)
    if ubigeo is None:
        return None

    row = distrito_data.loc[ubigeo].copy()
    row["personal_total"] = personal_total
    row["gasto_total"]    = gasto_total

    X = pd.DataFrame([row[features]])
    X[cat_cols] = encoder.transform(X[cat_cols])
    X[num_cols] = imputer.transform(X[num_cols])

    prob  = float(model.predict_proba(X)[0, 1])
    label = "ALTO RIESGO" if prob >= threshold else "BAJO RIESGO"

    return {
        "label": label,
        "prob":  prob,
        "anio_pred": int(row["anio"]) + 1,
        "departamento": row.get("departamento", "N/D"),
        "provincia":    row.get("provincia", "N/D"),
        "altitud":      row.get("altitude", np.nan),
        "macroregion":  row.get("macroregion_inei", "N/D"),
        "prevalencia":  row.get("prevalencia_anemia", np.nan),
        "ninos":        int(row.get("ninos_evaluados", 0)),
        "anio_datos":   int(row["anio"]),
    }


# ── UI ───────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Predictor de Anemia Distrital", layout="centered")
st.title("Predictor de Alto Riesgo de Anemia Distrital")
st.caption(
    "Selecciona un distrito peruano y ajusta las variables de política para ver "
    "cómo cambia la predicción de alto riesgo de anemia en el año siguiente."
)

nombre_distrito = st.selectbox("Distrito", nombre_list)

# Inicializar sliders con valores del distrito seleccionado
ubigeo_sel = ubigeo_map.get(nombre_distrito)
row_sel    = distrito_data.loc[ubigeo_sel]
personal_default = min(int(row_sel["personal_total"]) if not np.isnan(row_sel["personal_total"]) else 0, PERSONAL_MAX)
gasto_default    = min(int(row_sel["gasto_total"])    if not np.isnan(row_sel["gasto_total"])    else 0, GASTO_MAX)

st.markdown("### Variables de política")
personal_total = st.slider("Personal de salud (personal_total)", 0, PERSONAL_MAX, personal_default)
gasto_total    = st.slider("Gasto total en salud (S/)", 0, GASTO_MAX, gasto_default, step=100_000)

resultado = predecir(nombre_distrito, personal_total, gasto_total)

if resultado:
    st.divider()
    col1, col2, col3 = st.columns(3)
    color = "red" if resultado["label"] == "ALTO RIESGO" else "green"
    col1.metric("Clasificación", resultado["label"])
    col2.metric("Probabilidad", f"{resultado['prob']:.1%}")
    col3.metric("Año predicho", resultado["anio_pred"])

    st.markdown("### Información del distrito")
    prev_str = f"{resultado['prevalencia']:.1%}" if not np.isnan(resultado["prevalencia"]) else "N/D"
    altitud_str = f"{resultado['altitud']:.0f} msnm" if not np.isnan(resultado["altitud"]) else "N/D"

    st.markdown(
        f"**Departamento:** {resultado['departamento']}  |  "
        f"**Provincia:** {resultado['provincia']}  |  "
        f"**Altitud:** {altitud_str}  |  "
        f"**Macrorregión:** {resultado['macroregion']}"
    )
    st.markdown(
        f"**Último año con datos:** {resultado['anio_datos']}  \n"
        f"**Prevalencia anemia ({resultado['anio_datos']}):** {prev_str}  \n"
        f"**Niños evaluados:** {resultado['ninos']:,}  \n"
        f"**Personal de salud (ajustado):** {int(personal_total):,}  \n"
        f"**Gasto en salud (ajustado):** S/ {int(gasto_total):,}"
    )
