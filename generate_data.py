import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RNG = random.Random(20261111)
FIELDS = ['timestamp','service','level','trace_id','span_id','parent_span_id','event','message','duration_ms']
SCENARIOS = {
    'db_unavailable': [
        ('api-gateway','INFO','request_received','POST /orders accepted',12,None),
        ('order-service','INFO','create_order','Creating order',18,0),
        ('order-service','ERROR','db_connection_refused','PostgreSQL connection refused: db-orders:5432',220,1),
        ('order-service','ERROR','order_failed','Order creation failed due to database connection error',230,1),
        ('api-gateway','ERROR','upstream_503','order-service returned HTTP 503',245,0)],
    'auth_expired': [
        ('api-gateway','INFO','request_received','GET /profile accepted',8,None),
        ('auth-service','INFO','validate_token','Validating access token',14,0),
        ('auth-service','WARN','token_expired','JWT expired at validation time',19,1),
        ('api-gateway','WARN','unauthorized','Returning HTTP 401 for expired token',27,0)],
    'payment_timeout': [
        ('api-gateway','INFO','request_received','POST /checkout accepted',10,None),
        ('order-service','INFO','checkout','Initiating payment',25,0),
        ('payment-service','INFO','provider_request','Sending payment request to external provider',34,1),
        ('payment-service','ERROR','provider_timeout','Payment provider did not respond within 3000ms',3040,2),
        ('order-service','ERROR','checkout_failed','Checkout failed: payment-service timeout',3060,1),
        ('api-gateway','ERROR','upstream_504','Returning HTTP 504',3080,0)],
    'pool_exhausted': [
        ('api-gateway','INFO','request_received','GET /users accepted',9,None),
        ('user-service','INFO','get_users','Querying user database',20,0),
        ('user-service','WARN','pool_pressure','Connection pool utilization 100 percent',45,1),
        ('user-service','ERROR','pool_exhausted','Timed out waiting for a database connection from pool',1045,1),
        ('api-gateway','ERROR','upstream_503','user-service returned HTTP 503',1070,0)],
    'dependency_unavailable': [
        ('api-gateway','INFO','request_received','GET /orders accepted',11,None),
        ('order-service','INFO','load_order','Loading order with user profile',25,0),
        ('user-service','ERROR','connection_reset','Connection reset while serving user profile',65,1),
        ('order-service','ERROR','dependency_error','Cannot load profile: user-service connection reset',79,1),
        ('api-gateway','ERROR','upstream_502','Returning HTTP 502',95,0)],
    'normal': [
        ('api-gateway','INFO','request_received','GET /orders accepted',7,None),
        ('auth-service','INFO','token_valid','Access token validated',16,0),
        ('order-service','INFO','order_loaded','Order loaded successfully',42,0),
        ('api-gateway','INFO','response_200','Returning HTTP 200',55,0)],
}

def generate():
    records, labels = [], []
    start = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)
    scenario_names = list(SCENARIOS)
    for index in range(180):
        cause = scenario_names[index % len(scenario_names)]
        trace_id = f'trace-{index:04d}'
        base = start + timedelta(seconds=index * 40)
        steps = SCENARIOS[cause]
        spans = [f'{trace_id}-s{i}' for i in range(len(steps))]
        for j, (service, level, event, message, delay, parent) in enumerate(steps):
            records.append(dict(timestamp=(base + timedelta(milliseconds=delay)).isoformat(),
                service=service,level=level,trace_id=trace_id,span_id=spans[j],
                parent_span_id=spans[parent] if parent is not None else '',
                event=event,message=message,duration_ms=delay))
        labels.append({'trace_id':trace_id,'root_cause':cause,'is_incident':cause != 'normal'})
    RNG.shuffle(records)
    records += [dict(records[i]) for i in range(12)]
    for idx in [20, 80, 140, 200]: records[idx]['service'] = ''
    for idx in [30, 90, 150]: records[idx]['level'] = 'NOT_A_LEVEL'
    for idx in [40, 100]: records[idx]['timestamp'] = 'invalid-timestamp'
    ROOT.joinpath('data').mkdir(exist_ok=True)
    for name, fields, data in [('raw_logs.csv', FIELDS, records),
                                ('incident_labels.csv', ['trace_id','root_cause','is_incident'], labels)]:
        with (ROOT/'data'/name).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader(); writer.writerows(data)
    print(f'Generated {len(records)} raw log rows, {len(labels)} traces, {len(SCENARIOS)} scenarios')

if __name__ == '__main__': generate()
