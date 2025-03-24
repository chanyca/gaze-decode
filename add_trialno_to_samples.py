"""
Author: Ailene Chan
Date: 2025-01-02

What it does:
- Adds trial_no to samples csv
- Adds phase (f - fixation, s - stimulus, r - response) to samples csv
- Saves as new csv under `eyelink_csv`
"""

import pandas as pd
import os
import importlib
import get_df
importlib.reload(get_df)
gdf = get_df.DataFrame()

debug = True

# Define input and output directories
in_dir = os.path.join(os.getcwd(), 'edf/asc/ParseEyeLinkAsc')
out_dir = os.path.join(os.getcwd(), 'eyelink_csv')

# Get sample CSV files and unique subject IDs
samples_csvs = [f for f in os.listdir(in_dir) if f.endswith('Sample.csv')]
sids = list(set(f[:5] for f in samples_csvs))

# Process each subject
for sid in sids:
    print(f"\nProcessing {sid}...")
    
    # Load trial events and samples
    trial_event_df = gdf.trial_event(gdf.message(sid))
    sample_L_df = pd.read_csv(os.path.join(in_dir, f'{sid}L_Sample.csv'))
    sample_R_df = pd.read_csv(os.path.join(in_dir, f'{sid}R_Sample.csv'))
    
    # Combine left and right samples
    sample_df = pd.concat([sample_L_df, sample_R_df], ignore_index=True)
    sample_df['trial_no'] = None
    sample_df['phase'] = None

    print(sample_R_df.head()) if debug else None

    # Vectorized updates to 'trial_no' and 'phase'
    for _, row in trial_event_df.iterrows():
        trial_mask = (sample_df['tSample'] >= row['trial_start']) & (sample_df['tSample'] <= row['trial_end'])
        fixation_mask = (sample_df['tSample'] >= row['fix_start']) & (sample_df['tSample'] <= row['fix_end'])
        stimulus_mask = (sample_df['tSample'] >= row['stim_start']) & (sample_df['tSample'] <= row['stim_end'])
        response_mask = (sample_df['tSample'] >= row['resp_start']) & (sample_df['tSample'] <= row['resp_end'])

        # Assign trial_no and phase based on conditions
        sample_df.loc[trial_mask, 'trial_no'] = row['trial_no']
        sample_df.loc[fixation_mask, 'phase'] = 'f'
        sample_df.loc[stimulus_mask, 'phase'] = 's'
        sample_df.loc[response_mask, 'phase'] = 'r'

    # Filter rows within trials
    sample_df = sample_df.dropna(subset=['trial_no'])
    print(sample_df.head()) if debug else None

    # Save updated DataFrame
    os.makedirs(out_dir, exist_ok=True)
    output_path = os.path.join(out_dir, f'{sid}_Sample_trialno_phase.csv')
    sample_df.to_csv(output_path, index=False)
    print(f"Saved processed data to {output_path}")
