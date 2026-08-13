import pandas as pd
import pickle

df = pd.read_csv('data/clean/merged/panel_distrital_final.csv')

# Reproducir exactamente la construccion del panel
UMBRAL = 0.30
target_next = df[['ubigeo', 'anio', 'prevalencia_anemia']].copy()
target_next['anio'] = target_next['anio'] - 1
target_next = target_next.rename(columns={'prevalencia_anemia': 'prev_t1'})

panel = df.merge(target_next, on=['ubigeo', 'anio'], how='inner')
panel = panel.dropna(subset=['prev_t1', 'prevalencia_anemia'])
panel['alto_riesgo_t1'] = (panel['prev_t1'] >= UMBRAL).astype(int)

print('=== Una fila del panel para verificar ===')
ejemplo = panel[panel['ubigeo'] == 10101].sort_values('anio')
print(ejemplo[['ubigeo', 'anio', 'prevalencia_anemia', 'prev_t1', 'alto_riesgo_t1']].to_string())

print('\n=== Lo que significa cada columna ===')
print('  anio              -> año t (features son de este año)')
print('  prevalencia_anemia -> prevalencia EN año t  <-- ESTE es el lag')
print('  prev_t1           -> prevalencia EN año t+1 <-- este es el TARGET')
print('  alto_riesgo_t1    -> 1 si prev_t1 >= 30%')

# Verificar latest
with open('app/model_artifacts.pkl', 'rb') as f:
    art = pickle.load(f)
latest = art['latest']

print('\n=== En la app: latest por distrito (primer distrito como ejemplo) ===')
row = latest.iloc[0]
print(f'  ubigeo            : {row["ubigeo"]}')
print(f'  distrito          : {row["distrito"]}')
print(f'  anio (t)          : {row["anio"]}  <- año de los features')
print(f'  prevalencia_anemia: {row["prevalencia_anemia"]:.3f}  <- prevalencia del año {int(row["anio"])}')
print(f'  anio predicho (t+1): {int(row["anio"])+1}')

print('\n=== Distribucion del ultimo anio disponible por distrito ===')
print(latest['anio'].value_counts().sort_index())

print('\n=== Para los 77 distritos de alto riesgo ===')
X = latest[art['features']].copy()
X[art['cat_cols']] = art['encoder'].transform(X[art['cat_cols']])
X[art['num_cols']] = art['imputer'].transform(X[art['num_cols']])
latest2 = latest.copy()
latest2['prob'] = art['model'].predict_proba(X)[:, 1]
alto = latest2[latest2['prob'] >= art['threshold']]
print(alto[['distrito', 'anio', 'prevalencia_anemia', 'prob']].sort_values('prob', ascending=False).head(10).to_string())
print('\nAnio de los features usados para los de alto riesgo:')
print(alto['anio'].value_counts().sort_index())
