import pandas as pd

df = pd.read_csv('data/clean/merged/panel_distrital_final.csv')

UMBRAL = 0.30
target_next = df[['ubigeo', 'anio', 'prevalencia_anemia']].copy()
target_next['anio'] = target_next['anio'] - 1
target_next = target_next.rename(columns={'prevalencia_anemia': 'prev_t1'})
panel = df.merge(target_next, on=['ubigeo', 'anio'], how='inner')
panel = panel.dropna(subset=['prev_t1', 'prevalencia_anemia'])
panel['alto_riesgo_t1'] = (panel['prev_t1'] >= UMBRAL).astype(int)

print('=== Dataset t->t+1 ===')
res = panel.groupby('anio').agg(
    n_obs      =('ubigeo', 'count'),
    n_positivo =('alto_riesgo_t1', 'sum'),
    n_negativo =('alto_riesgo_t1', lambda x: (x==0).sum()),
    pct_pos    =('alto_riesgo_t1', 'mean'),
    ano_predicho=('anio', lambda x: x.iloc[0]+1)
).reset_index()
res['pct_pos'] = res['pct_pos'].map('{:.1%}'.format)
res = res.rename(columns={'anio':'ano_t', 'n_obs':'n', 'n_positivo':'positivos', 'n_negativo':'negativos'})
print(res[['ano_t','ano_predicho','n','positivos','negativos','pct_pos']].to_string(index=False))
print(f'\nTotal: {len(panel):,}')
