import pandas as pd
import numpy as np
import os

def clean_and_split():
    # Setup paths
    input_file = "C:/Users/USER/Documents/GetU.Grow/venv/grow_agent/data/funds_master.csv" # The file you just uploaded
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📂 Loading {input_file}...")
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print("❌ Error: funds_master.csv not found. Please upload it to the root folder.")
        return

    # 1. Clean up columns: Drop the broken score columns
    cols_to_drop = [c for c in df.columns if 'score_0_100' in c]
    df_clean = df.drop(columns=cols_to_drop)
    
    print(f"   Original columns cleaned. Using 'score_raw' as source.")

    # 2. Process each type separately
    fund_types = ['SH', 'PT', 'PU', 'CP']
    clean_dfs = []

    for f_type in fund_types:
        # Filter by type
        type_df = df_clean[df_clean['MFType'] == f_type].copy()
        
        if type_df.empty:
            print(f"⚠️ No funds found for {f_type}, skipping.")
            continue
            
        # Recalculate Score 0-100 strictly for this group
        min_s = type_df['score_raw'].min()
        max_s = type_df['score_raw'].max()
        
        if max_s > min_s:
            type_df['score_0_100'] = ((type_df['score_raw'] - min_s) / (max_s - min_s)) * 100
        else:
            type_df['score_0_100'] = 100.0 # Single fund case
            
        # Round for display
        type_df['score_0_100'] = type_df['score_0_100'].round(1)
        
        # Add Rank
        type_df = type_df.sort_values(by='score_0_100', ascending=False)
        type_df['rank'] = range(1, len(type_df) + 1)

        # Save individual file
        output_path = os.path.join(output_dir, f"funds_{f_type.lower()}.csv")
        type_df.to_csv(output_path, index=False)
        print(f"✅ Saved {f_type} ranking to: {output_path} ({len(type_df)} funds)")
        
        clean_dfs.append(type_df)

    # 3. Create Master Clean File (Overall)
    if clean_dfs:
        master_clean = pd.concat(clean_dfs, ignore_index=True)
        # For the overall master, we might want an 'overall_rank' or just keep type ranks.
        # Let's keep it simple for now.
        master_path = os.path.join(output_dir, "funds_master_clean.csv")
        master_clean.to_csv(master_path, index=False)
        print(f"🎉 Saved Master DB to: {master_path} ({len(master_clean)} funds)")
    else:
        print("❌ No data to save.")

if __name__ == "__main__":
    clean_and_split()