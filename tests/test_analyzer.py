import pandas as pd
import pytest
from src.parser import clean_logs
from src.analyzer import summarize_incident


def load():
    return clean_logs(pd.read_csv('data/raw_logs.csv'))


def test_cleaning():
    raw = pd.read_csv('data/raw_logs.csv')
    out = clean_logs(raw)
    assert len(out) == len(raw) - 21
    assert out['service'].notna().all()
    assert out['level'].isin({'DEBUG','INFO','WARN','ERROR','CRITICAL'}).all()
    assert out['timestamp'].notna().all()


def test_causal_trace():
    incident = summarize_incident(load(), 'trace-0000')
    assert incident['has_errors']
    assert incident['events'][0]['event'] == 'request_received'
    assert any(event['event'] == 'db_connection_refused' for event in incident['events'])
    assert any(event['event'] == 'upstream_503' for event in incident['events'])
    assert all('root_cause' not in event for event in incident['events'])


def test_normal_trace():
    incident = summarize_incident(load(), 'trace-0005')
    assert not incident['has_errors']


def test_unknown_trace():
    with pytest.raises(ValueError):
        summarize_incident(load(), 'missing')
