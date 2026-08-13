import json
with open('notebooks/02_anemia_and_spending_models/00d_xgboost_prevalencia.ipynb', encoding='utf-8') as f:
    nb = json.load(f)
for i, cell in enumerate(nb['cells']):
    src = ''.join(cell.get('source', ''))
    if 'train_df' in src or '2020' in src:
        print(i, cell.get('id', 'no-id'), repr(src[:120]))
        print()
