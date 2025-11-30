import pandas as pd
import numpy as np
import os

# --- 1. SETUP PATHS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# --- 2. LOAD DATA HELPER ---
def load_data(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)

# Load Metadata
try:
    print(f"Loading metadata from: {DATA_DIR}")
    WEIGHTS_DF = load_data("weights.csv")
    WEIGHTS_DICT = dict(zip(WEIGHTS_DF['feature'], WEIGHTS_DF['weight'])) if not WEIGHTS_DF.empty else {}

    OOS_DF = load_data("oos_reliability.csv")
    if 'MFType' in OOS_DF.columns and 'outofsample_oct24-oct25' in OOS_DF.columns:
        OOS_DICT = dict(zip(OOS_DF['MFType'], OOS_DF['outofsample_oct24-oct25']))
    else:
        OOS_DICT = {}

    print("✅ Metadata loaded successfully.")
except Exception as e:
    print(f"⚠️ Metadata Error: {e}")
    WEIGHTS_DICT = {}
    OOS_DICT = {}

# --- HELPER: JSON-SAFE CONVERTER ---
def to_native_type(val):
    if pd.isna(val) or val is None: return 0.0
    if isinstance(val, (np.integer, np.int64, np.int32)): return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)): return float(val)
    return val

def smart_round(val):
    val = to_native_type(val)
    if isinstance(val, float):
        if val == 0: return 0.0
        return float(f"{val:.2g}") if abs(val) < 0.1 else round(val, 2)
    return val

# --- 3. DEFINE TOOLS ---

def get_top_funds(fund_type: str) -> dict:
    """Retrieves top 5 funds for a specific category using CLEAN split files."""
    raw_input = str(fund_type).upper().strip()
    target_code = None
    
    # Map input
    if raw_input in ["SH", "SAHAM", "EQUITY"]: target_code = "sh"
    elif raw_input in ["PU", "PASAR UANG", "MONEY"]: target_code = "pu"
    elif raw_input in ["PT", "PENDAPATAN TETAP", "FIXED"]: target_code = "pt"
    elif raw_input in ["CP", "CAMPURAN", "BALANCED"]: target_code = "cp"
    
    if not target_code:
        if "SAHAM" in raw_input: target_code = "sh"
        elif "PASAR UANG" in raw_input: target_code = "pu"
        elif "PENDAPATAN" in raw_input: target_code = "pt"
        elif "CAMPURAN" in raw_input: target_code = "cp"
    
    if not target_code:
        return {"error": f"Invalid fund type '{fund_type}'."}

    df = load_data(f"funds_{target_code}.csv")
    if df.empty: return {"error": f"Database for {target_code.upper()} not found."}
    
    top = df.head(5)
    
    result = []
    for _, row in top.iterrows():
        result.append({
            "mfName": row['mfName'],
            "score": smart_round(row['score_0_100']),
            "rank": int(row['rank'])
        })
    return {"status": "success", "data": result}


def get_fund_analysis(fund_name: str) -> dict:
    """Retrieves deep analysis."""
    df = load_data("funds_master_clean.csv")
    if df.empty: return {"error": "Master database not loaded."}

    mask = df['mfName'].str.contains(fund_name, case=False, na=False)
    matches = df[mask]
    if matches.empty: return {"error": f"Fund '{fund_name}' not found."}
    
    row = matches.iloc[0]
    
    fund_features = {}
    for feature, weight in WEIGHTS_DICT.items():
        if feature in row:
            fund_features[feature] = smart_round(row[feature])

    return {
        "fund_name": str(row['mfName']),
        "type": str(row['MFType']),
        "ai_score": smart_round(row.get('score_0_100', 0)),
        "historical_alpha_top_vs_rest": smart_round(OOS_DICT.get(row['MFType'], 0)),
        "analysis_data": {
            "global_weights": WEIGHTS_DICT,
            "fund_specifics": fund_features
        }
    }

# --- NEW TOOL: PARTNER INFO ---
def get_partner_info(partner_name: str) -> dict:
    """
    Retrieves info about channel partners (sales, promos, benefits).
    Args:
        partner_name: 'Bibit', 'Bareksa', 'Bank', or 'All'.
    """
    # In a real app, this would query a CMS or API.
    # For now, we simulate the data as requested.
    partners = {
        "BIBIT": {
            "name": "Bibit",
            "promo": "Cashback GoPay 50rb for new users.",
            "benefits": "Robo-advisor tailored to your risk profile, free transfer fees.",
            "link": "https://bibit.id"
        },
        "BAREKSA": {
            "name": "Bareksa",
            "promo": "OVO Points 25rb for first purchase > 500rb.",
            "benefits": "Wide range of funds, comprehensive analytical tools.",
            "link": "https://bareksa.com"
        },
        "BANK": {
            "name": "Bank Partners (BCA, Mandiri)",
            "promo": "Special rate for auto-debit plans.",
            "benefits": "Integrated with your mobile banking, trusted security.",
            "link": "https://bank-partner.com"
        }
    }
    
    key = partner_name.upper().strip()
    if key == "ALL":
        return partners
    
    # Fuzzy match
    for p_key, data in partners.items():
        if key in p_key or p_key in key:
            return data
            
    return {"error": f"Partner '{partner_name}' not found. Try 'Bibit', 'Bareksa', or 'Bank'."}

# --- NEW TOOL: VISUALIZATION ---
def get_visualization_data(viz_type: str, fund_names: str = None) -> dict:
    """
    Generates data for frontend visualization.
    Args:
        viz_type: 'performance_comparison' (Top 10% vs Rest) or 'head_to_head'.
        fund_names: Comma-separated list of funds for 'head_to_head'.
    """
    if viz_type == 'performance_comparison':
        # Returns the Alpha (OOS Reliability) stats
        # This shows how much better the Top 10% funds are compared to the Rest 90%
        return {
            "type": "bar_chart",
            "title": "Model Performance: Top 10% Funds vs Market Average (Alpha)",
            "x_axis": "Fund Type",
            "y_axis": "Excess Return (Alpha)",
            "data": OOS_DICT # {'SH': 0.24, ...}
        }
    
    elif viz_type == 'head_to_head':
        if not fund_names:
            return {"error": "fund_names required for head_to_head."}
        
        df = load_data("funds_master_clean.csv")
        if df.empty: return {"error": "DB not loaded."}
        
        names = [n.strip() for n in fund_names.split(',')]
        # Find funds
        comparison_data = []
        for name in names:
            mask = df['mfName'].str.contains(name, case=False, na=False)
            matches = df[mask]
            if not matches.empty:
                row = matches.iloc[0]
                comparison_data.append({
                    "name": row['mfName'],
                    "score": smart_round(row.get('score_0_100', 0)),
                    "return_6m": smart_round(row.get('ret_6m', 0)),
                    "value_added": smart_round(row.get('value_added', 0))
                })
        
        return {
            "type": "comparison_table",
            "title": "Head-to-Head Comparison",
            "data": comparison_data
        }

    return {"error": "Invalid viz_type."}