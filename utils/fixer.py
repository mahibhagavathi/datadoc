"""
Applies approved fixes. Reads issue['selected_fix_action'] for specific action,
falls back to sensible defaults per issue title.
"""

import pandas as pd
import numpy as np
import re

NULL_TOKENS = {"n/a", "na", "none", "null", "unknown", "-", "--", "?", "nil"}
EMAIL_RE    = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def apply_fix(df: pd.DataFrame, issue: dict) -> pd.DataFrame:
    df     = df.copy()
    col    = issue.get("column", "")
    title  = issue.get("title", "")
    action = issue.get("selected_fix_action", "default")

    try:
        # ── STRUCTURAL ────────────────────────────────────────────────────────
        if title == "Exact Duplicate Rows":
            if action == "drop_dupes_keep_last":
                df = df.drop_duplicates(keep="last").reset_index(drop=True)
            elif action == "flag_dupes":
                df["is_duplicate"] = df.duplicated(keep=False)
            else:
                df = df.drop_duplicates(keep="first").reset_index(drop=True)

        elif title == "Primary Key Violations":
            if col in df.columns:
                if action == "pk_keep_last":
                    df = df.drop_duplicates(subset=[col], keep="last").reset_index(drop=True)
                elif action == "pk_flag":
                    df[f"{col}_duplicate"] = df.duplicated(subset=[col], keep=False)
                else:
                    df = df.drop_duplicates(subset=[col], keep="first").reset_index(drop=True)

        elif title in ("Completely Empty Column", "Constant Column", "Near-Constant Column",
                       "Accidental Index Column Export"):
            if col in df.columns and action != "skip_builtin":
                df = df.drop(columns=[col])

        elif title == "Unnamed Columns (Likely Index Export)":
            unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
            df = df.drop(columns=[c for c in unnamed if c in df.columns])

        elif title == "Completely Empty Rows":
            df = df.dropna(how="all").reset_index(drop=True)

        elif title == "Corrupted / Excel Error Values":
            EXCEL_ERRORS = {"#NULL!", "#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#NUM!", "#N/A"}
            if col in df.columns:
                df[col] = df[col].apply(lambda x: np.nan if str(x) in EXCEL_ERRORS else x)

        elif title == "Repeated Header Row Mid-File":
            if col in df.columns:
                df = df[df[col].astype(str).str.strip() != str(col).strip()].reset_index(drop=True)

        # ── NULLS ─────────────────────────────────────────────────────────────
        elif title == "High Null Rate":
            if col in df.columns:
                numeric = pd.to_numeric(df[col], errors="coerce")
                if action == "fill_median":
                    df[col] = df[col].fillna(numeric.median())
                elif action == "fill_mean":
                    df[col] = df[col].fillna(round(numeric.mean(), 2))
                elif action == "fill_zero":
                    df[col] = df[col].fillna(0)
                elif action == "drop_null_rows":
                    df = df.dropna(subset=[col]).reset_index(drop=True)
                elif action == "fill_unknown":
                    df[col] = df[col].fillna("Unknown")
                else:  # fill_mode / default
                    mode = df[col].mode()
                    df[col] = df[col].fillna(mode[0] if len(mode) else "Unknown")

        elif title == "String Null Tokens in Column":
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: np.nan if pd.notna(x) and str(x).strip().lower() in NULL_TOKENS else x
                )

        elif title == "Null Values in ID Column":
            if col in df.columns:
                df = df.dropna(subset=[col]).reset_index(drop=True)

        # ── VALIDITY ──────────────────────────────────────────────────────────
        elif title == "Negative Values in Non-Negative Column":
            if col in df.columns:
                numeric = pd.to_numeric(df[col], errors="coerce")
                if action == "neg_to_abs":
                    df[col] = numeric.abs()
                elif action == "neg_drop_rows":
                    df = df[pd.to_numeric(df[col], errors="coerce") >= 0].reset_index(drop=True)
                else:  # neg_to_nan
                    df[col] = numeric.apply(lambda x: np.nan if pd.notna(x) and x < 0 else x)

        elif title == "Extreme / Impossible Values":
            if col in df.columns:
                numeric = pd.to_numeric(df[col], errors="coerce")
                q1, q99 = numeric.quantile(0.01), numeric.quantile(0.99)
                if action == "extreme_to_nan":
                    df[col] = numeric.apply(lambda x: np.nan if pd.notna(x) and (x < q1 * 10 or x > q99 * 10) else x)
                elif action == "extreme_drop_rows":
                    mask = (numeric >= q1) & (numeric <= q99 * 10)
                    df = df[mask | numeric.isna()].reset_index(drop=True)
                else:  # cap_percentile
                    df[col] = numeric.clip(lower=numeric.quantile(0.01), upper=numeric.quantile(0.99))

        elif title == "Future Dates in Historical Column":
            if col in df.columns:
                parsed = pd.to_datetime(df[col], errors="coerce")
                parsed[parsed > pd.Timestamp.now()] = pd.NaT
                df[col] = parsed

        elif title == "Invalid Email Addresses":
            if col in df.columns:
                if action == "invalid_email_drop":
                    df = df[df[col].apply(lambda x: pd.isna(x) or bool(EMAIL_RE.match(str(x))))].reset_index(drop=True)
                else:
                    df[col] = df[col].apply(lambda x: x if pd.isna(x) or EMAIL_RE.match(str(x)) else np.nan)

        elif title == "Inconsistent Phone Number Formats":
            if col in df.columns:
                if action == "phone_flag":
                    df[f"{col}_valid"] = df[col].apply(
                        lambda x: bool(re.match(r"[\d\s\+\-\(\)]{7,}", str(x))) if pd.notna(x) else False
                    )
                else:  # phone_digits
                    df[col] = df[col].apply(
                        lambda x: re.sub(r"[^\d]", "", str(x)) if pd.notna(x) else x
                    )

        # ── CONSISTENCY ───────────────────────────────────────────────────────
        elif title == "Inconsistent Category Casing":
            if col in df.columns:
                if action == "lower_case":
                    df[col] = df[col].str.strip().str.lower()
                elif action == "upper_case":
                    df[col] = df[col].str.strip().str.upper()
                else:  # title_case
                    df[col] = df[col].str.strip().str.title()

        elif title == "Leading / Trailing Whitespace":
            if col in df.columns:
                df[col] = df[col].str.strip()

        elif title == "Mixed Date Formats":
            if col in df.columns:
                parsed = pd.to_datetime(df[col], errors="coerce")
                if action == "date_dmy":
                    df[col] = parsed.dt.strftime("%d/%m/%Y")
                else:
                    df[col] = parsed.dt.strftime("%Y-%m-%d")

        elif title == "Boolean Value Inconsistency":
            if col in df.columns:
                bool_map = {"true":True,"yes":True,"y":True,"1":True,"t":True,
                            "false":False,"no":False,"n":False,"0":False,"f":False}
                mapped = df[col].astype(str).str.lower().map(bool_map)
                if action == "bool_10":
                    df[col] = mapped.map({True:1, False:0})
                elif action == "bool_yesno":
                    df[col] = mapped.map({True:"Yes", False:"No"})
                else:
                    df[col] = mapped

        elif title == "Numeric Column Stored as String":
            if col in df.columns:
                if action == "cast_int":
                    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
                else:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

        elif title == "Currency Symbols in Numeric Column":
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r"[\$€£¥,]", "", regex=True)
                df[col] = pd.to_numeric(df[col], errors="coerce")

        elif title == "Comma-Formatted Numbers as Strings":
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(",", "")
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # ── NAMING ────────────────────────────────────────────────────────────
        elif title == "Column Names with Special Characters / Spaces":
            df.columns = [re.sub(r"[^a-zA-Z0-9]", "_", str(c)).lower().strip("_") for c in df.columns]

        elif title == "Inconsistent Column Name Casing":
            if action == "col_snake":
                df.columns = [re.sub(r"[^a-zA-Z0-9]", "_", str(c)).lower().strip("_") for c in df.columns]
            else:
                df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]

        # ── REDUNDANCY ────────────────────────────────────────────────────────
        elif title in ("Possibly Redundant Columns", "Redundant Date Component Column"):
            if action != "skip_builtin" and "&" in str(col):
                parts   = str(col).replace("[","").replace("]","").replace("'","").split("&")
                to_drop = parts[-1].strip()
                if to_drop in df.columns:
                    df = df.drop(columns=[to_drop])

        elif title == "Statistical Outliers (IQR)":
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                df[col] = df[col].clip(lower=q1 - 3*iqr, upper=q3 + 3*iqr)

    except Exception:
        pass  # never crash the app

    return df
