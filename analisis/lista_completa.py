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
latest['prob'] = model.predict_proba(X)[:, 1]
latest['anio_predicho'] = latest['anio'] + 1

alto = (
    latest[latest['prob'] >= threshold]
    [['distrito', 'provincia', 'departamento', 'anio_predicho', 'prevalencia_anemia', 'prob']]
    .sort_values('prob', ascending=False)
    .reset_index(drop=True)
)
alto.index += 1
alto['prevalencia_anemia'] = alto['prevalencia_anemia'].map('{:.1%}'.format)
alto['prob'] = alto['prob'].map('{:.1%}'.format)
alto.columns = ['Distrito', 'Provincia', 'Departamento', 'Ano predicho', 'Prev. actual', 'Prob. alto riesgo']
print(alto.to_string())
