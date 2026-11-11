import pandas as pd

VALID_LEVELS = {"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}

def clean_logs(df: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "service", "level", "trace_id", "message"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    out = df.copy().drop_duplicates()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    for col in ("service", "level", "trace_id", "message"):
        out[col] = out[col].astype("string").str.strip()
        out[col] = out[col].replace("", pd.NA)
    out = out.dropna(subset=["timestamp", "service", "level", "trace_id", "message"])
    out = out[out["level"].isin(VALID_LEVELS)]
    return out.sort_values("timestamp").reset_index(drop=True)
