import json

with open('notebooks/02_anemia_and_spending_models/00d_xgboost_prevalencia.ipynb', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] != 'code':
        continue
    for out in cell.get('outputs', []):
        text = out.get('text', out.get('data', {}).get('text/plain', ''))
        if isinstance(text, list):
            text = ''.join(text)
        if 'SHAP importancia' in text:
            print(f'--- Cell {i} ---')
            print(text[:1500])
