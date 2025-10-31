import matplotlib
import platform

# merge_and_report.py
import argparse, glob, os, re, sys, logging
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import yaml
from datetime import datetime

def set_korean_font():
    sys_plat = platform.system()
    if sys_plat == "Windows":
        font_name = "Malgun Gothic"
    elif sys_plat == "Darwin":  # macOS
        font_name = "AppleGothic"
    else:  # Linux
        font_name = "NanumGothic"
    matplotlib.rcParams["font.family"] = font_name
    matplotlib.rcParams["axes.unicode_minus"] = False  # 마이너스 깨짐 방지

# ────────────────────────────── 공통 경로 ──────────────────────────────
BASE = Path(__file__).resolve().parent
INBOX = BASE / "inbox"
OUTPUT = BASE / "output"
CONFIG = BASE / "config.yaml"
OUTPUT.mkdir(exist_ok=True)

# ────────────────────────────── 로깅 ──────────────────────────────
logging.basicConfig(
    filename=OUTPUT / "run.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger().addHandler(console)

def load_config():
    if not CONFIG.exists():
        logging.error("config.yaml이 없습니다. 경로: %s", CONFIG)
        sys.exit(1)
    with open(CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def find_first_existing_column(df, candidates):
    for c in candidates:
        # 대소문자/공백 차이 허용
        if c in df.columns:
            return c
        # 느슨한 매칭: 소문자 비교
        lower_map = {col.lower().strip(): col for col in df.columns}
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None

def normalize_columns(df, cfg):
    mapping = cfg["column_mapping"]
    std_cols = {}
    for std, candidates in mapping.items():
        col = find_first_existing_column(df, candidates)
        if col is None:
            logging.warning("필수/대상 컬럼을 찾을 수 없음: %s", std)
            std_cols[std] = None
        else:
            std_cols[std] = col

    # 존재하는 컬럼만 선택 후 표준명으로 rename
    selected = {std: src for std, src in std_cols.items() if src is not None}
    ndf = df[list(selected.values())].rename(columns={v: k for k, v in selected.items()})
    # 없는 표준 컬럼은 일단 만들어 둔다(검증에서 걸러질 것)
    for std in mapping.keys():
        if std not in ndf.columns:
            ndf[std] = pd.NA
    return ndf

def cast_types(df, cfg):
    t = cfg.get("types", {})
    for col, typ in t.items():
        if col not in df.columns:
            continue
        if typ == "datetime":
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif typ == "numeric":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif typ == "string":
            df[col] = df[col].astype("string")
    return df

def extract_meta_from_filename(fname: str, cfg):
    pattern_dept = cfg["filename_regex"]["dept"]
    pattern_month = cfg["filename_regex"]["month"]
    dept_match = re.search(pattern_dept, fname)
    month_match = re.search(pattern_month, fname)
    dept = dept_match.group("dept") if dept_match else None
    month_raw = month_match.group("month") if month_match else None
    # month 표준화: 2025-09, 202509, 2025_09 → 2025-09
    month = None
    if month_raw:
        digits = re.sub(r"[^0-9]", "", month_raw)  # 202509
        if len(digits) == 6:
            month = f"{digits[:4]}-{digits[4:]}"
    return dept, month

def validate(df, cfg):
    rules = cfg["validation"]
    errors = []
    # 필수 컬럼 체크
    for col in rules.get("required_columns", []):
        if col not in df.columns:
            errors.append(f"필수 컬럼 누락: {col}")
    # 타입/결측 체크
    if "date" in df.columns:
        if df["date"].isna().any():
            errors.append("날짜 파싱 실패 행 존재")
    for col in ("qty", "amount"):
        if col in df.columns and df[col].isna().any():
            errors.append(f"{col} 결측치 존재")
    # 음수 허용 여부
    if not rules.get("allow_negative_qty", False) and "qty" in df.columns:
        if (df["qty"] < 0).any():
            errors.append("음수 수량 존재")
    if not rules.get("allow_negative_amount", False) and "amount" in df.columns:
        if (df["amount"] < 0).any():
            errors.append("음수 금액 존재")
    return errors

def load_file(path: Path, cfg):
    # 확장자에 따라 읽기
    sheet = cfg.get("sheet_name", 0)
    if path.suffix.lower() in [".xlsx", ".xlsm", ".xls"]:
        df = pd.read_excel(path, sheet_name=sheet)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path, encoding="utf-8")
    else:
        logging.info("지원하지 않는 확장자: %s", path.name)
        return pd.DataFrame()

    df = normalize_columns(df, cfg)
    df = cast_types(df, cfg)
    # 파일명으로부터 dept, month 보강
    dept_from_name, month_from_name = extract_meta_from_filename(path.name, cfg)
    if "dept" in df.columns and df["dept"].isna().all() and dept_from_name:
        df["dept"] = dept_from_name
    if month_from_name and "date" in df.columns and df["date"].notna().any():
        # 기준월 불일치 검증은 나중에 target_month와 비교
        pass
    df["_source_file"] = path.name
    return df

def month_str(dt: pd.Timestamp):
    return dt.strftime("%Y-%m")

def filter_by_target_month(df, target_month):
    # target_month: YYYY-MM
    mask = df["date"].dt.strftime("%Y-%m") == target_month
    return df[mask]

def save_charts(df, cfg, target_month):
    charts = cfg.get("charts", {})
    topn = int(charts.get("top_n_products", 10))

    # 제품별 매출 TOP N
    prod = (df.groupby("product")["amount"]
              .sum().sort_values(ascending=False).head(topn))
    plt.figure(figsize=(10,5))
    prod.plot(kind="bar")
    plt.title(f"[{target_month}] 제품별 매출 TOP{topn}")
    plt.xlabel("제품")
    plt.ylabel("매출")
    plt.tight_layout()
    out1 = OUTPUT / f"{target_month}_sales_by_product.png"
    plt.savefig(out1, dpi=150)
    plt.close()

    # 일자별 매출 추이
    by_date = (df.groupby(df["date"].dt.date)["amount"]
                 .sum().sort_index())
    plt.figure(figsize=(10,5))
    by_date.plot(kind="line", marker="o")
    plt.title(f"[{target_month}] 일자별 매출 추이")
    plt.xlabel("일자")
    plt.ylabel("매출")
    plt.tight_layout()
    out2 = OUTPUT / f"{target_month}_sales_by_date.png"
    plt.savefig(out2, dpi=150)
    plt.close()

    logging.info("차트 저장: %s, %s", out1.name, out2.name)
    return out1, out2

def main():
    set_korean_font()
    parser = argparse.ArgumentParser(description="엑셀 합치기 + 월간 리포트 자동 생성")
    parser.add_argument("--month", help="처리 기준월 YYYY-MM (예: 2025-09)")
    args = parser.parse_args()

    cfg = load_config()
    target_month = args.month or cfg.get("target_month")
    if not re.match(r"^20\d{2}-(0[1-9]|1[0-2])$", str(target_month)):
        logging.error("기준월 형식 오류. 예: 2025-09")
        sys.exit(1)
    files = sorted([Path(p) for p in glob.glob(str(INBOX / "*"))])
    if not files:
        logging.error("inbox 폴더에 파일이 없습니다. 경로: %s", INBOX)
        sys.exit(1)

    logging.info("처리 시작 | 기준월=%s | 파일수=%d", target_month, len(files))

    frames = []
    for f in files:
        try:
            df = load_file(f, cfg)
            if df.empty:
                logging.warning("데이터가 비었거나 읽기 실패: %s", f.name)
                continue
            frames.append(df)
            logging.info("로딩 완료: %s (%d행)", f.name, len(df))
        except Exception as e:
            logging.exception("파일 처리 실패: %s | %s", f.name, e)

    if not frames:
        logging.error("유효한 데이터가 없습니다.")
        sys.exit(1)

    raw = pd.concat(frames, ignore_index=True)

    # 검증 및 분리 저장
    errs = validate(raw, cfg)
    if errs:
        logging.warning("초기 검증 경고: %s", "; ".join(errs))

    # 필수 컬럼 없으면 바로 중단
    for col in cfg["validation"]["required_columns"]:
        if col not in raw.columns:
            logging.error("필수 컬럼이 없어 중단: %s", col)
            sys.exit(1)

    # 기준월 필터
    raw = raw.dropna(subset=["date"])
    monthly = filter_by_target_month(raw, target_month)

    if monthly.empty:
        logging.error("기준월(%s)에 해당하는 데이터가 없습니다.", target_month)
        # 참고용으로 원본 몇 행이라도 저장
        raw.to_csv(OUTPUT / "raw_fallback.csv", index=False, encoding="utf-8-sig")
        sys.exit(1)

    # 결측치/음수 행 분리
    rejected_mask = monthly["qty"].isna() | monthly["amount"].isna() | (monthly["qty"] < 0) | (monthly["amount"] < 0)
    rejected = monthly[rejected_mask]
    monthly_clean = monthly[~rejected_mask]

    if not rejected.empty:
        rejected.to_csv(OUTPUT / f"{target_month}_rejected.csv", index=False, encoding="utf-8-sig")
        logging.info("검증 탈락 행 저장: %d행", len(rejected))

    # 집계
    summary = (monthly_clean.groupby("product")["amount"]
               .sum().sort_values(ascending=False).reset_index(name="amount"))
    by_dept = (monthly_clean.groupby("dept")["amount"]
               .sum().sort_values(ascending=False).reset_index(name="amount"))
    by_date = (monthly_clean.groupby(monthly_clean["date"].dt.date)["amount"]
               .sum().reset_index(name="amount").rename(columns={"date":"day"}))

    # 엑셀 저장
    xlsx_path = OUTPUT / f"{target_month}_monthly_report.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
        monthly_clean.to_excel(w, index=False, sheet_name="raw")
        summary.to_excel(w, index=False, sheet_name="summary_by_product")
        by_dept.to_excel(w, index=False, sheet_name="summary_by_dept")
        by_date.to_excel(w, index=False, sheet_name="summary_by_date")

    logging.info("엑셀 저장: %s", xlsx_path.name)

    # 차트 저장
    save_charts(monthly_clean, cfg, target_month)

    # 보너스: 콘솔에 핵심 요약 찍기
    total = float(monthly_clean["amount"].sum())
    topn = summary.head(5)
    print("\n=== 월간 리포트 요약 ===")
    print(f"기준월: {target_month}")
    print(f"총 매출액: {total:,.0f}")
    print("TOP5 제품:")
    for _, r in topn.iterrows():
        print(f" - {r['product']}: {r['amount']:,.0f}")
    print(f"\n결과물 폴더: {OUTPUT}")

if __name__ == "__main__":
    main()
