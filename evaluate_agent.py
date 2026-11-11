import argparse
import csv
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

LABELS = Path(__file__).resolve().parent / 'data' / 'incident_labels.csv'
OUTPUT = Path(__file__).resolve().parent / 'results'

PATTERNS = {
    'db_unavailable': ['connection refused', 'failed to connect to postgresql', 'db_connection_refused', 'недоступност', 'отказ подключения', 'не смог подключиться', 'не удалось подключиться'],
    'auth_expired': ['token expired', 'expired token', 'token presented', 'token was expired', 'was expired at validation', 'истек', 'истёк', 'просрочен', 'auth_expired'],
    'payment_timeout': ['payment timeout', 'payment-service timeout', 'платёжный провайдер не ответил', 'платежный провайдер не ответил', 'таймаут в payment-service', 'тайм-аут в payment-service', 'тайм-аут платеж', 'таймаут платеж', 'payment_timeout'],
    'pool_exhausted': ['pool exhausted', 'connection pool', 'пул соединений', 'pool_exhausted', 'истощение пула', 'исчерпание пула'],
    'dependency_unavailable': ['dependency unavailable', 'upstream unavailable', 'сервис недоступен', 'зависимост', 'dependency_unavailable'],
    'normal': ['no incident', 'no error', 'no failure', 'ошибок нет', 'ошибки отсутствуют', 'сбоев не обнаружено', 'нормальн', 'штатн', 'insufficient_evidence'],
}


def classify(cause: str) -> str:
    value = cause.casefold()
    matches = [name for name, patterns in PATTERNS.items() if any(p in value for p in patterns)]
    return matches[0] if len(matches) == 1 else 'unclassified'


def select_traces(labels: list[dict], per_class: int) -> list[dict]:
    selected, counts = [], Counter()
    for item in labels:
        if counts[item['root_cause']] < per_class:
            selected.append(item)
            counts[item['root_cause']] += 1
    return selected


def evaluate(records: list[dict]) -> dict:
    completed = [r for r in records if r['status'] == 'ok']
    classified = [r for r in completed if r['predicted_label'] != 'unclassified']
    correct = sum(r['correct'] for r in completed)
    by_class = {}
    for label in sorted(set(r['expected_label'] for r in records)):
        subset = [r for r in completed if r['expected_label'] == label]
        by_class[label] = {
            'completed': len(subset),
            'correct': sum(r['correct'] for r in subset),
            'unclassified': sum(r['predicted_label'] == 'unclassified' for r in subset),
        }
    return {
        'attempted': len(records), 'completed': len(completed),
        'failed': len(records) - len(completed),
        'correct': correct,
        'accuracy_over_completed': round(correct / len(completed), 4) if completed else None,
        'accuracy_over_attempted': round(correct / len(records), 4) if records else None,
        'classified': len(classified),
        'by_class': by_class,
        'note': 'Heuristic keyword scoring, not independent expert assessment; review misclassifications manually.',
    }


def main():
    parser = argparse.ArgumentParser(description='Evaluate actual OpenRouter diagnoses on synthetic labelled traces')
    parser.add_argument('--per-class', type=int, default=2, help='Traces per category (default 2 => 12 API calls)')
    parser.add_argument('--delay', type=float, default=1, help='Seconds between API calls')
    parser.add_argument('--output', type=Path, default=None)
    parser.add_argument('--rescore', type=Path, default=None, help='Re-evaluate saved JSON without API calls')
    parser.add_argument('--retry-failed', type=Path, default=None, help='Retry only failed records from saved JSON')
    parser.add_argument('--max-retries', type=int, default=2, help='Additional attempts per failed record on rate limit (default 2)')
    args = parser.parse_args()
    if args.rescore and args.retry_failed:
        parser.error('--rescore and --retry-failed are mutually exclusive')
    if args.max_retries < 0:
        parser.error('--max-retries must be nonnegative')
    if args.per_class < 1 or args.delay < 0:
        parser.error('--per-class must be positive and --delay nonnegative')

    if args.rescore is not None:
        payload = json.loads(args.rescore.read_text(encoding='utf-8'))
        for record in payload['records']:
            if record['status'] == 'ok':
                record['predicted_label'] = classify(record['diagnosis']['suspected_cause'])
                record['correct'] = record['predicted_label'] == record['expected_label']
        payload['summary'] = evaluate(payload['records'])
        output = args.output or args.rescore.with_name(args.rescore.stem + '_rescored.json')
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print('SUMMARY:', json.dumps(payload['summary'], ensure_ascii=False, indent=2))
        print('Saved:', output)
        return

    load_dotenv(override=True)
    from src.agent import diagnose

    if args.retry_failed:
        source = json.loads(args.retry_failed.read_text(encoding='utf-8'))
        records = source['records']
        cases = [(i, r) for i, r in enumerate(records) if r['status'] == 'error']
        out = args.output or args.retry_failed.with_name(args.retry_failed.stem + '_retried.json')
        if out.resolve() == args.retry_failed.resolve():
            parser.error('Output must differ from retry input')
    else:
        with LABELS.open(newline='', encoding='utf-8') as handle:
            selected = select_traces(list(csv.DictReader(handle)), args.per_class)
        records = []
        cases = [(None, case) for case in selected]
        out = args.output or OUTPUT / datetime.now(timezone.utc).strftime('evaluation_%Y%m%d_%H%M%S.json')
    if not cases:
        print('No failed records to retry.' if args.retry_failed else 'No labelled traces')
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    for index, (record_index, case) in enumerate(cases, start=1):
        trace_id = case['trace_id']
        print(f'[{index}/{len(cases)}] {trace_id} ({case.get("root_cause", case.get("expected_label"))})', flush=True)
        start = time.monotonic()
        attempts = 0
        while True:
            attempts += 1
            try:
                diagnosis = diagnose(trace_id)
                break
            except Exception as exc:
                rate_limited = '429' in str(exc) or 'RateLimit' in type(exc).__name__
                if not rate_limited or attempts > args.max_retries:
                    diagnosis = None
                    last_error = exc
                    break
                wait = max(args.delay, 30.0) * (2 ** (attempts - 1))
                print(f'  -> 429, waiting {wait:.0f}s before retry ({attempts}/{args.max_retries})', flush=True)
                time.sleep(wait)
        try:
            if diagnosis is None:
                raise last_error
            result = diagnosis.model_dump()
            predicted = classify(diagnosis.suspected_cause)
            record = {'trace_id': trace_id, 'expected_label': case.get('root_cause', case.get('expected_label')),
                      'predicted_label': predicted, 'correct': predicted == case.get('root_cause', case.get('expected_label')),
                      'status': 'ok', 'duration_seconds': round(time.monotonic() - start, 2),
                      'diagnosis': result}
        except Exception as exc:
            record = {'trace_id': trace_id, 'expected_label': case.get('root_cause', case.get('expected_label')),
                      'predicted_label': None, 'correct': False, 'status': 'error',
                      'duration_seconds': round(time.monotonic() - start, 2),
                      'error': f'{type(exc).__name__}: {exc}'}
        record['api_attempts'] = attempts
        if record_index is None:
            records.append(record)
        else:
            records[record_index] = record
        payload = {'summary': evaluate(records), 'records': records}
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print('  ->', record['predicted_label'] if record['status'] == 'ok' else record['error'], flush=True)
        if index < len(cases):
            time.sleep(args.delay)
    print('\nSUMMARY:', json.dumps(evaluate(records), ensure_ascii=False, indent=2))
    print('Saved:', out)


if __name__ == '__main__':
    main()
