import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.preprocessing import OrdinalEncoder
from sklearn.impute import SimpleImputer
import shap

df = pd.read_csv('data/clean/merged/panel_distrital_final.csv')

UMBRAL = 0.30
target_next = df[['ubigeo', 'anio', 'prevalencia_anemia']].copy()
target_next['anio'] = target_next['anio'] - 1
target_next = target_next.rename(columns={'prevalencia_anemia': 'prev_t1'})
panel = df.merge(target_next, on=['ubigeo', 'anio'], how='inner')
panel = panel.dropna(subset=['prev_t1', 'prevalencia_anemia'])
panel['alto_riesgo_t1'] = (panel['prev_t1'] >= UMBRAL).astype(int)

TARGET  = 'alto_riesgo_t1'
EXCLUIR = ['ubigeo', 'anio', 'ninos_con_anemia', 'ninos_sin_anemia', 'prev_t1', TARGET]
features = [c for c in panel.columns if c not in EXCLUIR]
cat_cols = [c for c in features if panel[c].dtype == 'object']
num_cols = [c for c in features if panel[c].dtype != 'object']

train_df = panel[panel.anio.isin([2020, 2021, 2022])]
val_df   = panel[panel.anio == 2023]
test_df  = panel[panel.anio.isin([2024, 2025])]

enc = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
imp = SimpleImputer(strategy='median')

def preprocess(train, val, test):
    Xtr = train[features].copy()
    Xva = val[features].copy()
    Xte = test[features].copy()
    Xtr[cat_cols] = enc.fit_transform(Xtr[cat_cols])
    Xva[cat_cols] = enc.transform(Xva[cat_cols])
    Xte[cat_cols] = enc.transform(Xte[cat_cols])
    Xtr[num_cols] = imp.fit_transform(Xtr[num_cols])
    Xva[num_cols] = imp.transform(Xva[num_cols])
    Xte[num_cols] = imp.transform(Xte[num_cols])
    return Xtr, Xva, Xte

X_train, X_val, X_test = preprocess(train_df, val_df, test_df)
y_train = train_df[TARGET].values
y_val   = val_df[TARGET].values

neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
scale_pos = neg / pos

model = XGBClassifier(
    n_estimators=500, learning_rate=0.05, max_depth=4,
    subsample=0.75, colsample_bytree=0.75, min_child_weight=15,
    gamma=1.0, reg_alpha=1.0, reg_lambda=5.0,
    scale_pos_weight=scale_pos, eval_metric='aucpr',
    tree_method='hist', random_state=42, n_jobs=-1
)
model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

# Feature importance gain
fmap   = {f'f{i}': f for i, f in enumerate(features)}
scores = model.get_booster().get_score(importance_type='gain')
fi_gain = pd.Series({fmap.get(k, k): v for k, v in scores.items()}).sort_values(ascending=False)

# SHAP sobre test
explainer   = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
shap_imp = pd.Series(np.abs(shap_values).mean(axis=0), index=features).sort_values(ascending=False)

print('=== TOP 15 SHAP ===')
print(shap_imp.head(15).round(4).to_string())

print('\n=== TOP 10 GAIN ===')
print(fi_gain.head(10).round(2).to_string())

# Union
top15_shap = set(shap_imp.head(15).index)
top10_gain = set(fi_gain.head(10).index)
candidates = list(top15_shap | top10_gain)
print(f'\n=== UNION: {len(candidates)} features ===')
print(sorted(candidates))

# Correlacion entre numericas candidatas
num_cand = [f for f in candidates if panel[f].dtype != 'object']
Xtr_cand = X_train[num_cand]
corr_m = Xtr_cand.corr().abs()
upper  = corr_m.where(np.triu(np.ones(corr_m.shape), k=1).astype(bool))

to_drop = set()
for col in upper.columns:
    for row in upper.index:
        val = upper.loc[row, col]
        if pd.notna(val) and val >= 0.90:
            loser = col if shap_imp.get(col, 0) < shap_imp.get(row, 0) else row
            to_drop.add(loser)
            print(f'  Correlacion {row} <-> {col} = {val:.3f} | eliminar: {loser}')

features_final = [f for f in candidates if f not in to_drop]
print(f'\n=== FEATURES FINALES: {len(features_final)} ===')
for f in sorted(features_final, key=lambda x: -shap_imp.get(x, 0)):
    kind = 'cat' if panel[f].dtype == 'object' else 'num'
    print(f'  {f:35s} SHAP={shap_imp.get(f,0):.4f}  GAIN={fi_gain.get(f,0):.1f}  [{kind}]')
