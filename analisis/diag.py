import pandas as pd
import numpy as np

df = pd.read_csv('data/clean/merged/panel_distrital_final.csv')

print('=== NULOS POR COLUMNA ===')
nulos = df.isnull().sum()
pct = (nulos / len(df) * 100).round(1)
res = pd.DataFrame({'n_nulos': nulos, 'pct': pct}).sort_values('pct', ascending=False)
print(res[res.pct > 0].to_string())

print('\n=== VARIANZA CERO O CASI CERO ===')
num = df.select_dtypes(include='number')
for col in num.columns:
    cv = num[col].std() / (abs(num[col].mean()) + 1e-9)
    if cv < 0.01:
        print(f'  {col}: CV={cv:.4f}  unique={num[col].nunique()}')

print('\n=== CORRELACIONES ALTAS (>0.90) entre predictores ===')
corr = num.drop(columns=['ubigeo', 'anio']).corr().abs()
upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
high = []
for c in upper.columns:
    for r in upper.index:
        val = upper.loc[r, c]
        if pd.notna(val) and val > 0.90:
            high.append((c, r, val))
for c1, c2, v in sorted(high, key=lambda x: -x[2]):
    print(f'  {c1} <-> {c2}: {v:.3f}')

print('\n=== COLUMNAS FIJAS POR UBIGEO (no varían en el tiempo) ===')
geo_cols = [
    'departamento', 'provincia', 'distrito', 'region', 'macroregion_inei',
    'macroregion_minsa', 'capital', 'latitude', 'longitude', 'altitude',
    'superficie', 'pob_densidad_2020', 'pct_cultivo', 'pct_construido',
    'pct_desnudo', 'pct_agua_visible', 'n_edificios', 'area_construida_m2',
    'confianza_media', 'area_distrito_km2', 'densidad_edificios_km2',
    'elevacion_media', 'pendiente_media', 'pct_agua_permanente', 'pct_agua_estacional'
]
for col in geo_cols:
    if col in df.columns:
        n_var = df.groupby('ubigeo')[col].nunique()
        if (n_var == 1).all():
            print(f'  {col} -> fija por ubigeo')

print('\n=== VALORES UNICOS MUY BAJOS ===')
for col in num.columns:
    if num[col].nunique() <= 3:
        print(f'  {col}: {sorted(num[col].dropna().unique())}')
