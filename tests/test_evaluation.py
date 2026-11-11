from evaluate_agent import classify, select_traces, evaluate


def test_classifier_specific():
    assert classify('PostgreSQL connection refused: db-orders:5432') == 'db_unavailable'
    assert classify('Token expired at auth-service') == 'auth_expired'
    assert classify('Payment timeout') == 'payment_timeout'
    assert classify('Connection pool exhausted') == 'pool_exhausted'
    assert classify('No error, request completed normally') == 'normal'
    assert classify('Something happened') == 'unclassified'


def test_ambiguous_is_unclassified():
    assert classify('Connection refused, connection pool exhausted') == 'unclassified'


def test_selection_balanced():
    labels = [{'trace_id': str(i), 'root_cause': c} for i, c in enumerate(['a','a','b','b','a','b'])]
    assert [x['trace_id'] for x in select_traces(labels, 1)] == ['0', '2']


def test_evaluate_counts():
    rows = [{'expected_label':'a','predicted_label':'a','correct':True,'status':'ok'},
            {'expected_label':'b','predicted_label':'unclassified','correct':False,'status':'ok'},
            {'expected_label':'b','predicted_label':None,'correct':False,'status':'error'}]
    result = evaluate(rows)
    assert result['attempted'] == 3
    assert result['completed'] == 2
    assert result['correct'] == 1
    assert result['accuracy_over_completed'] == 0.5


def test_real_multilingual_diagnoses():
    assert classify('order-service failed to connect to PostgreSQL at db-orders:5432, causing order creation failure and an upstream HTTP 503 from api-gateway.') == 'db_unavailable'
    assert classify('The request failed because the access token presented to auth-service was expired at validation time, causing api-gateway to return HTTP 401.') == 'auth_expired'
    assert classify('Внешний платёжный провайдер не ответил в течение 3000 мс, что вызвало таймаут в payment-service и каскадный сбой checkout в order-service и api-gateway.') == 'payment_timeout'


def test_russian_pool_exhaustion_diagnosis():
    assert classify('Истощение пула соединений к БД в user-service: пул достиг 100% утилизации') == 'pool_exhausted'
