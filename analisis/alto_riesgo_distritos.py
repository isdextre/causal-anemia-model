import pickle
import numpy as np
import pandas as pd

with open('app/model_artifacts.pkl', 'rb') as f:
    art = pickle.load(f)

model     = art['model']
encoder   = art['encoder']
imputer   = art['imputer']
features  = art['features']
cat_cols  = art['cat_cols']
num_cols  = art['num_cols']
threshold = art['threshold']
latest    = art['latest']

X = latest[features].copy()
X[cat_cols] = encoder.transform(X[cat_cols])
X[num_cols] = imputer.transform(X[num_cols])

latest = latest.copy()
latest['prob_alto_riesgo'] = model.predict_proba(X)[:, 1]
latest['prediccion']       = (latest['prob_alto_riesgo'] >= threshold).map({True: 'ALTO RIESGO', False: 'bajo riesgo'})
latest['anio_predicho']    = latest['anio'] + 1

alto = (
    latest[latest['prediccion'] == 'ALTO RIESGO']
    [['distrito', 'provincia', 'departamento', 'macroregion_inei',
      'anio', 'anio_predicho', 'prevalencia_anemia', 'prob_alto_riesgo']]
    .sort_values('prob_alto_riesgo', ascending=False)
    .reset_index(drop=True)
)

alto['prevalencia_anemia'] = alto['prevalencia_anemia'].map('{:.1%}'.format)
alto['prob_alto_riesgo']   = alto['prob_alto_riesgo'].map('{:.1%}'.format)

print(f'Distritos predichos como ALTO RIESGO: {len(alto):,}')
print(f'Threshold usado: {threshold:.3f}')
print(f'Anios predichos: {sorted(alto["anio_predicho"].unique())}')
print()
print(alto.head(30).to_string(index=True))
print()
print('--- Por macroregion ---')
print(alto.groupby('macroregion_inei').size().sort_values(ascending=False))
print()
print('--- Por departamento ---')
print(alto.groupby('departamento').size().sort_values(ascending=False).head(10))
