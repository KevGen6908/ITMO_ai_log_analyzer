from pathlib import Path
import json
import pandas as pd
ROOT = Path(__file__).resolve().parent
raw = pd.read_csv(ROOT/'data/raw_logs.csv')
clean = pd.read_csv(ROOT/'data/cleaned_logs.csv')
labels = pd.read_csv(ROOT/'data/incident_labels.csv')
report = {
 'raw_rows': len(raw), 'clean_rows': len(clean), 'removed_rows': len(raw)-len(clean),
 'raw_exact_duplicates': int(raw.duplicated().sum()),
 'raw_missing_service': int(raw.service.isna().sum()),
 'raw_invalid_levels': int((~raw.level.isin(['DEBUG','INFO','WARN','ERROR','CRITICAL'])).sum()),
 'raw_invalid_timestamps': int(pd.to_datetime(raw.timestamp,errors='coerce',utc=True).isna().sum()),
 'traces': int(clean.trace_id.nunique()),
 'services': {k:int(v) for k,v in clean.service.value_counts().items()},
 'levels': {k:int(v) for k,v in clean.level.value_counts().items()},
 'scenario_counts': {k:int(v) for k,v in labels.root_cause.value_counts().items()},
 'traces_with_errors': int(clean.groupby('trace_id')['level'].apply(lambda x:x.isin(['ERROR','CRITICAL']).any()).sum()),
}
(ROOT/'data/eda_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
