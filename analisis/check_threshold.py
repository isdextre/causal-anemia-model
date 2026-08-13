import pandas as pd
df = pd.read_csv('data/clean/merged/panel_distrital_final.csv')
for t in [0.20, 0.25, 0.30, 0.40]:
    pos = (df['prevalencia_anemia'] >= t).sum()
    total = df['prevalencia_anemia'].notna().sum()
    print(f'Umbral {t:.0%}: positivos={pos:,} ({pos/total:.1%}) | negativos={total-pos:,} ({(total-pos)/total:.1%})')
