import pandas as pd
import numpy as np

df = pd.read_csv('data/clean/merged/panel_distrital_final.csv')

# Construir dataset t -> t+1
df_t  = df.copy()
df_t1 = df[['ubigeo', 'anio', 'prevalencia_anemia']].copy()
df_t1['anio_pred'] = df_t1['anio']
df_t1 = df_t1.rename(columns={'prevalencia_anemia': 'prev_t1'})

merged = df_t.merge(
    df_t1[['ubigeo', 'anio_pred', 'prev_t1']],
    left_on=['ubigeo', 'anio'],
    right_on=['ubigeo', 'anio_pred'],
    how='inner'
)
# anio en merged es t, prev_t1 es prevalencia en t+1
# pero necesitamos anio_pred = anio + 1
merged2 = df_t.merge(
    df_t1[['ubigeo', 'anio_pred', 'prev_t1']].assign(anio=lambda x: x['anio_pred'] - 1),
    on=['ubigeo', 'anio'],
    how='inner'
)
merged2 = merged2.dropna(subset=['prev_t1', 'prevalencia_anemia'])
merged2['alto_riesgo_t1'] = (merged2['prev_t1'] >= 0.30).astype(int)

print('Pares t -> t+1 disponibles:', len(merged2))
print('Anos como t (predictores):', sorted(merged2['anio'].unique()))
print('Positivos por ano predicho:')
for g, grp in merged2.groupby('anio'):
    print(f'  t={g} -> t+1={g+1}: positivos={grp["alto_riesgo_t1"].mean():.1%} n={len(grp)}')
