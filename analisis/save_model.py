import pandas as pd
import numpy as np
import pickle
from xgboost import XGBClassifier
from sklearn.preprocessing import OrdinalEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import precision_recall_curve, precision_score, recall_score, accuracy_score

df = pd.read_csv('data/clean/merged/panel_distrital_final.csv')

UMBRAL = 0.30
target_next = df[['ubigeo', 'anio', 'prevalencia_anemia']].copy()
target_next['anio'] = target_next['anio'] - 1
target_next = target_next.rename(columns={'prevalencia_anemia': 'prev_t1'})
panel = df.merge(target_next, on=['ubigeo', 'anio'], how='inner')
panel = panel.dropna(subset=['prev_t1', 'prevalencia_anemia'])
panel['alto_riesgo_t1'] = (panel['prev_t1'] >= UMBRAL).astype(int)

TARGET = 'alto_riesgo_t1'

# prevalencia_anemia(t) incluida como lag legitimo — es la prevalencia del año t, NO de t+1
features = [
    'prevalencia_anemia',
    'altitude',
    'ninos_evaluados',
    'gasto_total',
    'pct_agua_visible',
    'area_construida_m2',
    'pct_agua_permanente',
    'personal_total',
    'superficie',
    'provincia',
    'densidad_edificios_km2',
    'pct_desnudo',
    'latitude',
    'longitude',
    'macroregion_minsa',
    'macroregion_inei',
]
cat_cols = [c for c in features if panel[c].dtype == 'object']
num_cols = [c for c in features if panel[c].dtype != 'object']

train_df = panel[panel.anio.isin([2020, 2021, 2022, 2023])]
val_df   = panel[panel.anio == 2024]
test_df  = panel[panel.anio == 2025]

enc = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
imp = SimpleImputer(strategy='median')

X_train = train_df[features].copy()
X_val   = val_df[features].copy()
X_test  = test_df[features].copy()
y_train = train_df[TARGET].values
y_val   = val_df[TARGET].values
y_test  = test_df[TARGET].values

X_train[cat_cols] = enc.fit_transform(X_train[cat_cols])
X_val[cat_cols]   = enc.transform(X_val[cat_cols])
X_test[cat_cols]  = enc.transform(X_test[cat_cols])
X_train[num_cols] = imp.fit_transform(X_train[num_cols])
X_val[num_cols]   = imp.transform(X_val[num_cols])
X_test[num_cols]  = imp.transform(X_test[num_cols])

neg, pos = (y_train == 0).sum(), (y_train == 1).sum()

model = XGBClassifier(
    n_estimators=1000, learning_rate=0.03, max_depth=3,
    subsample=0.70, colsample_bytree=0.70, min_child_weight=40,
    gamma=2.0, reg_alpha=2.0, reg_lambda=15.0,
    scale_pos_weight=neg/pos, eval_metric='aucpr',
    early_stopping_rounds=50, tree_method='hist',
    random_state=42, n_jobs=-1
)
model.fit(X_train, y_train, eval_set=[(X_train, y_train), (X_val, y_val)], verbose=False)
print(f'Mejor iteracion: {model.best_iteration}  |  Mejor val PR-AUC: {model.best_score:.4f}')

# Threshold optimo sobre val
prob_val  = model.predict_proba(X_val)[:, 1]
prob_test = model.predict_proba(X_test)[:, 1]
prec_v, rec_v, thresh_v = precision_recall_curve(y_val, prob_val)
mask = rec_v[:-1] >= 0.30
best_thresh = float(thresh_v[mask][np.argmax(prec_v[:-1][mask])]) if mask.any() else 0.5
print(f'Threshold optimo: {best_thresh:.3f}')

# Metricas finales
for y_true, prob, split in [(y_train, model.predict_proba(X_train)[:,1], 'Train'),
                             (y_val,   prob_val,  'Val  '),
                             (y_test,  prob_test, 'Test ')]:
    pred = (prob >= best_thresh).astype(int)
    print(f'{split} | Precision={precision_score(y_true,pred,zero_division=0):.4f}  '
          f'Recall={recall_score(y_true,pred,zero_division=0):.4f}  '
          f'Accuracy={accuracy_score(y_true,pred):.4f}')

# Ultimos datos por distrito para la app
latest = (
    panel.sort_values('anio')
         .groupby('ubigeo')
         .last()
         .reset_index()
)
latest['nombre'] = (
    latest['distrito'].fillna('') + ' (' +
    latest['provincia'].fillna('') + ')'
)

artifacts = {
    'model'        : model,
    'encoder'      : enc,
    'imputer'      : imp,
    'features'     : features,
    'cat_cols'     : cat_cols,
    'num_cols'     : num_cols,
    'threshold'    : best_thresh,
    'latest'       : latest,
    'umbral_anemia': UMBRAL,
}
with open('app/model_artifacts.pkl', 'wb') as f:
    pickle.dump(artifacts, f)

print('\nArtefactos guardados en app/model_artifacts.pkl')
print(f'Features: {len(features)} (sin prevalencia_anemia)')
