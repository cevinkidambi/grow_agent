import pandas as pd
import os
import glob

def clean_and_merge():
    raw_dir = "raw_data"
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    
    print("🚀 Starting Strict Data Cleaning...")

    # --- 1. Process Metadata (Weights & OOS) ---
    # These are just for the Analyst Agent to explain things
    try:
        w_files = glob.glob(f"{raw_dir}/*weights*.csv")
        if w_files:
            pd.read_csv(w_files[0]).to_csv(f"{output_dir}/weights.csv", index=False)
            print("✅ Weights processed.")
            
        oos_files = glob.glob(f"{raw_dir}/*oos_review*.csv")
        if oos_files:
            pd.read_csv(oos_files[0]).to_csv(f"{output_dir}/oos_reliability.csv", index=False)
            print("✅ OOS Reliability processed.")
    except Exception as e:
        print(f"⚠️ Metadata error: {e}")

    # --- 2. Process Funds (STRICTLY PER TYPE) ---
    fund_types = ['sh', 'pt', 'pu', 'cp']
    all_funds = []

    for f_type in fund_types:
        print(f"\nProcessing Type: {f_type.upper()}...")
        
        # A. LOAD SCORING FILE (The Source of Truth for Rank)
        score_path = os.path.join(raw_dir, f"fund-scoring-by-type_cv_{f_type}.csv")
        
        # B. LOAD FEATURES FILE (Only for "Why" context)
        feat_path = os.path.join(raw_dir, f"fund-scoring-by-type_cv_features_{f_type}.csv")

        if not os.path.exists(score_path):
            print(f"   ❌ Missing SCORING file for {f_type}. Skipping.")
            continue

        try:
            # 1. Read Scores
            df_score = pd.read_csv(score_path)
            # Clean spaces
            df_score.columns = df_score.columns.str.strip()
            
            # 2. Generate UI Score (0-100) strictly from 'score_raw'
            # We normalize relative to THIS TYPE only.
            # Formula: (Score - Min) / (Max - Min) * 100
            min_s = df_score['score_raw'].min()
            max_s = df_score['score_raw'].max()
            
            # Avoid division by zero if only 1 fund exists
            if max_s > min_s:
                df_score['score_0_100'] = ((df_score['score_raw'] - min_s) / (max_s - min_s)) * 100
            else:
                df_score['score_0_100'] = 100.0 # Default if single fund
            
            df_score['score_0_100'] = df_score['score_0_100'].round(1)

            # 3. Merge Features (Left Join)
            # We keep ALL rows from Scoring file. We only add columns from Features.
            if os.path.exists(feat_path):
                df_feat = pd.read_csv(feat_path)
                df_feat.columns = df_feat.columns.str.strip()
                
                # We drop 'score_raw' from features if it exists there, 
                # to prevent conflicts. We TRUST the scoring file.
                if 'score_raw' in df_feat.columns:
                    df_feat = df_feat.drop(columns=['score_raw'])
                
                # Merge
                merge_keys = ['mfName']
                if 'MFType' in df_feat.columns:
                    merge_keys.append('MFType')
                    
                merged_df = pd.merge(df_score, df_feat, on=merge_keys, how='left')
            else:
                print(f"   ⚠️ Features file missing for {f_type}, keeping scores only.")
                merged_df = df_score

            all_funds.append(merged_df)
            print(f"   ✅ Processed {len(merged_df)} funds.")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    # --- 3. Save Master File ---
    if all_funds:
        master_df = pd.concat(all_funds, ignore_index=True)
        output_path = f"{output_dir}/funds_master.csv"
        master_df.to_csv(output_path, index=False)
        print(f"\n🎉 Success! Consolidated DB saved at: {output_path}")
        print(f"   Total Funds: {len(master_df)}")
    else:
        print("\n❌ Error: No data processed.")

if __name__ == "__main__":
    clean_and_merge()