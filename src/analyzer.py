import pandas as pd

def summarize_incident(df: pd.DataFrame, trace_id: str) -> dict:
    incident = df.loc[df['trace_id'] == trace_id].sort_values('timestamp')
    if incident.empty:
        raise ValueError(f'Unknown trace_id: {trace_id}')
    columns = ['timestamp','service','level','span_id','parent_span_id','event','message','duration_ms']
    columns = [col for col in columns if col in incident.columns]
    events = []
    for record in incident[columns].to_dict('records'):
        events.append({key: (None if pd.isna(value) else str(value)) for key,value in record.items()})
    return {'trace_id': trace_id, 'services': sorted(incident['service'].unique().tolist()),
            'has_errors': bool(incident['level'].isin(['ERROR','CRITICAL']).any()),
            'events': events}
