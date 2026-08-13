import pandas as pd
import numpy as np

df = pd.read_csv('data/clean/merged/panel_distrital_final.csv')

for col in df.columns:
    s = df[col]
    dtype = str(s.dtype)
    n_null = s.isnull().sum()
    pct_null = n_null / len(df) * 100
    if dtype == 'object':
        ejemplos = s.dropna().unique()[:4]
        print(f'{col:30s} | {dtype:8s} | nulos: {pct_null:5.1f}% | ej: {list(ejemplos)}')
    else:
        print(f'{col:30s} | {dtype:8s} | nulos: {pct_null:5.1f}% | min={s.min():.2f}  mean={s.mean():.2f}  max={s.max():.2f}')
