import json
import pytest
pytest.importorskip('langchain')
from src.agent import get_trace, get_service_errors, Diagnosis

def test_trace_tool_hides_ground_truth():
    payload = json.loads(get_trace.invoke({'trace_id':'trace-0000'}))
    assert payload['trace_id'] == 'trace-0000'
    assert 'root_cause' not in json.dumps(payload)
    assert 'known_cause' not in json.dumps(payload)

def test_service_tool_limits_results():
    records = json.loads(get_service_errors.invoke({'service':'order-service','trace_id':'trace-0000','limit':2}))
    assert len(records) <= 2

def test_diagnosis_validation():
    with pytest.raises(Exception):
        Diagnosis.model_validate({'trace_id':'x','evidence':'wrong type'})


def test_cross_trace_errors_are_time_scoped():
    records = json.loads(get_service_errors.invoke({
        'service': 'user-service', 'trace_id': 'trace-0004', 'limit': 20
    }))
    assert all('pool_exhausted' not in str(r) for r in records)
    assert all(r['trace_id'] != 'trace-0004' for r in records)


def test_cross_trace_tool_requires_trace_id():
    result = get_service_errors.invoke({'service': 'user-service', 'trace_id': ''})
    assert 'required' in result
