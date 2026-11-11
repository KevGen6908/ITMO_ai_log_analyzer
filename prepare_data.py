from pathlib import Path
import pandas as pd
from src.parser import clean_logs

root = Path(__file__).resolve().parent
raw = pd.read_csv(root/'data/raw_logs.csv')
cleaned = clean_logs(raw)
cleaned.to_csv(root/'data/cleaned_logs.csv', index=False)
print(f'Raw rows: {len(raw)}; cleaned rows: {len(cleaned)}; removed: {len(raw)-len(cleaned)}')
print('Levels:', cleaned['level'].value_counts().to_dict())
print('Services:', cleaned['service'].value_counts().to_dict())
print('Unique traces:', cleaned['trace_id'].nunique())
