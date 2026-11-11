import argparse
import json
import pandas as pd
from dotenv import load_dotenv
from src.parser import clean_logs
from src.analyzer import summarize_incident

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trace', default='trace-0000')
    parser.add_argument('--llm', action='store_true', help='Run LangChain agent via OpenRouter')
    args = parser.parse_args()
    load_dotenv()
    if args.llm:
        from src.agent import diagnose
        print(diagnose(args.trace).model_dump_json(indent=2))
    else:
        df = clean_logs(pd.read_csv('data/cleaned_logs.csv'))
        print(json.dumps(summarize_incident(df,args.trace),ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
