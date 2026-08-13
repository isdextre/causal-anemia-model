import pickle
import numpy as np
import pandas as pd
import gradio as gr

# ── Cargar artefactos ────────────────────────────────────────────────────────
with open("app/model_artifacts.pkl", "rb") as f:
    art = pickle.load(f)

model       = art["model"]
encoder     = art["encoder"]
imputer     = art["imputer"]
features    = art["features"]
cat_cols    = art["cat_cols"]
num_cols    = art["num_cols"]
threshold   = art["threshold"]
latest      = art["latest"]
UMBRAL      = art["umbral_anemia"]

# Mapa nombre -> ubigeo y ubigeo -> fila
latest = latest.sort_values("nombre")
nombre_list   = latest["nombre"].tolist()
ubigeo_map    = dict(zip(latest["nombre"], latest["ubigeo"]))
distrito_data = latest.set_index("ubigeo")

# Rangos para sliders (P5 – P95 del panel)
PERSONAL_MIN = 0
PERSONAL_MAX = int(latest["personal_total"].quantile(0.95))
GASTO_MIN    = 0
GASTO_MAX    = int(latest["gasto_total"].quantile(0.95))


# ── Prediccion ───────────────────────────────────────────────────────────────
def predecir(nombre_distrito, personal_total, gasto_total):
    ubigeo = ubigeo_map.get(nombre_distrito)
    if ubigeo is None:
        return "Distrito no encontrado", "", "", "", ""

    row = distrito_data.loc[ubigeo].copy()
    anio_datos = int(row["anio"])

    # Aplicar valores ajustados por el usuario
    row["personal_total"] = personal_total
    row["gasto_total"]    = gasto_total

    # Construir DataFrame con las features
    X = pd.DataFrame([row[features]])

    # Encoding + imputacion
    X[cat_cols] = encoder.transform(X[cat_cols])
    X[num_cols] = imputer.transform(X[num_cols])

    prob  = float(model.predict_proba(X)[0, 1])
    label = "🔴 ALTO RIESGO" if prob >= threshold else "🟢 BAJO RIESGO"

    # Info del distrito
    prev_actual = row.get("prevalencia_anemia", np.nan)
    prev_str    = f"{prev_actual:.1%}" if not np.isnan(prev_actual) else "N/D"

    info = (
        f"**Departamento:** {row.get('departamento', 'N/D')}  |  "
        f"**Provincia:** {row.get('provincia', 'N/D')}  |  "
        f"**Altitud:** {row.get('altitude', 'N/D'):.0f} msnm  |  "
        f"**Macrorregión:** {row.get('macroregion_inei', 'N/D')}"
    )

    datos_base = (
        f"**Ultimo año con datos:** {anio_datos}  \n"
        f"**Prevalencia anemia ({anio_datos}):** {prev_str}  \n"
        f"**Niños evaluados:** {int(row.get('ninos_evaluados', 0)):,}  \n"
        f"**Personal salud (ajustado):** {int(personal_total):,}  \n"
        f"**Gasto salud (ajustado):** S/ {int(gasto_total):,}"
    )

    prob_str = f"{prob:.1%}"
    anio_pred = anio_datos + 1

    return (
        label,
        prob_str,
        str(anio_pred),
        info,
        datos_base,
    )


def cargar_distrito(nombre_distrito):
    """Carga los valores actuales del distrito para inicializar sliders."""
    ubigeo = ubigeo_map.get(nombre_distrito)
    if ubigeo is None:
        return 0, 0
    row = distrito_data.loc[ubigeo]
    personal = row.get("personal_total", 0)
    gasto    = row.get("gasto_total", 0)
    personal = 0 if np.isnan(personal) else int(personal)
    gasto    = 0 if np.isnan(gasto)    else int(gasto)
    return (
        gr.update(value=min(personal, PERSONAL_MAX)),
        gr.update(value=min(gasto, GASTO_MAX)),
    )


# ── UI ───────────────────────────────────────────────────────────────────────
CSS = """
#resultado { font-size: 2rem; font-weight: bold; text-align: center; padding: 12px; border-radius: 8px; }
#prob      { font-size: 1.4rem; text-align: center; }
"""

with gr.Blocks(title="Predictor de Anemia Distrital") as demo:

    gr.Markdown("# Predictor de Alto Riesgo de Anemia Distrital")
    gr.Markdown(
        "Selecciona un distrito peruano y ajusta las variables de política para ver "
        "cómo cambia la predicción de alto riesgo de anemia en el año siguiente."
    )

    with gr.Row():
        with gr.Column(scale=1):
            distrito_dd = gr.Dropdown(
                choices=nombre_list,
                label="Distrito",
                value=nombre_list[0],
                filterable=True,
            )

            gr.Markdown("### Variables de política")
            personal_sl = gr.Slider(
                minimum=PERSONAL_MIN,
                maximum=PERSONAL_MAX,
                step=1,
                label="Personal de salud (personal_total)",
                info="Trabajadores de salud en el distrito",
            )
            gasto_sl = gr.Slider(
                minimum=GASTO_MIN,
                maximum=GASTO_MAX,
                step=100_000,
                label="Gasto total en salud (S/)",
                info="Presupuesto ejecutado en salud",
            )

            btn = gr.Button("Predecir", variant="primary")

        with gr.Column(scale=1):
            gr.Markdown("### Prediccion para el siguiente ano")
            anio_out    = gr.Textbox(label="Año predicho", interactive=False)
            resultado   = gr.Textbox(label="Clasificacion", elem_id="resultado", interactive=False)
            prob_out    = gr.Textbox(label="Probabilidad de alto riesgo", elem_id="prob", interactive=False)

            gr.Markdown("### Informacion del distrito")
            info_out    = gr.Markdown()
            datos_out   = gr.Markdown()

    # Al cambiar distrito, inicializar sliders con datos reales
    distrito_dd.change(
        fn=cargar_distrito,
        inputs=distrito_dd,
        outputs=[personal_sl, gasto_sl],
    )

    # Predecir al hacer click
    btn.click(
        fn=predecir,
        inputs=[distrito_dd, personal_sl, gasto_sl],
        outputs=[resultado, prob_out, anio_out, info_out, datos_out],
    )

    # Predecir en tiempo real al mover sliders
    for sl in [personal_sl, gasto_sl]:
        sl.release(
            fn=predecir,
            inputs=[distrito_dd, personal_sl, gasto_sl],
            outputs=[resultado, prob_out, anio_out, info_out, datos_out],
        )

    # Cargar primer distrito al inicio
    demo.load(
        fn=lambda: cargar_distrito(nombre_list[0]),
        outputs=[personal_sl, gasto_sl],
    )

if __name__ == "__main__":
    demo.launch(share=False)
