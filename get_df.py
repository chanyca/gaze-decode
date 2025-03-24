import os
import pandas as pd

class DataFrame:
    def __init__(self):
        self.cwd = os.getcwd()
        self.eyedir = os.path.join(self.cwd, 'edf/asc/ParseEyeLinkAsc')
    
    def message(self, sid):
        message_L_df = pd.read_csv(f'{self.eyedir}/{sid}L_Message.csv')
        message_R_df = pd.read_csv(f'{self.eyedir}/{sid}R_Message.csv')
        # combine but add a column to indicate eye
        message_L_df['eye'] = 'L'
        message_R_df['eye'] = 'R'
        message_df = pd.concat([message_L_df, message_R_df], ignore_index=True)
        return message_df
    
    def trial_event(self, message_df):        
        trial_events = message_df[message_df['text'].str.contains("TRIALID|FIX_START|FIX_END|FIX FAILED|FIX_SUCCEED|STIM_START|STIM_END|RESP_START|RESP_END|TRIAL_END")]
        # print(trial_events)

        event_keys = {
            "FIX_START": "fix_start",
            "FIX FAILED": "fix_failed", # Note missing underscore, I didn't think too hard when writing eyelink messages (sigh...)
            "FIX_SUCCEED": "fix_succeed",
            "FIX_END": "fix_end",
            "STIM_START": "stim_start",
            "STIM_END": "stim_end",
            "RESP_START": "resp_start",
            "RESP_END": "resp_end",
            "TRIAL_END": "trial_end",
        }

        trial_event_list = []
        current_trial = None
        for _, row in trial_events.iterrows():
            if "TRIALID" in row['text']:
                current_trial = int(row['text'].split()[1])
                trial_event_list.append({
                    'trial_no': current_trial,
                    'eye': row['eye'],  # Keep eye information
                    'trial_start': row['time'] if "TRIALID" in row['text'] else None,
                    'trial_end': None,
                    'fix_start': None,
                    'fix_failed': None,
                    'fix_succeed': None,
                    'fix_end': None,
                    'stim_start': None,
                    'stim_end': None,
                    'resp_start': None,
                    'resp_end': None,
                })
            elif current_trial is not None:
                for keyword, key in event_keys.items():
                    if keyword in row['text']:
                        # Append a new entry for each eye-event combination
                        trial_event_list.append({
                            'trial_no': current_trial,
                            'eye': row['eye'],  # Eye-specific data
                            'trial_start': None,
                            'trial_end': row['time'] if key == 'trial_end' else None,
                            'fix_start': row['time'] if key == 'fix_start' else None,
                            'fix_failed': row['time'] if key == 'fix_failed' else None,
                            'fix_succeed': row['time'] if key == 'fix_succeed' else None,
                            'fix_end': row['time'] if key == 'fix_end' else None,
                            'stim_start': row['time'] if key == 'stim_start' else None,
                            'stim_end': row['time'] if key == 'stim_end' else None,
                            'resp_start': row['time'] if key == 'resp_start' else None,
                            'resp_end': row['time'] if key == 'resp_end' else None,
                        })
                        break

        # Convert trial events list to DataFrame
        trial_event_df = pd.DataFrame(trial_event_list)
        trial_event_df = trial_event_df.groupby(['eye', 'trial_no'], as_index=False).first()
        return trial_event_df
    
    def saccade_by_trial(self, sid, trial_event_df):
        """
        Columns:
        eye, tStart, tEnd, duration, xStart, yStart, xEnd, yEnd, ampDeg, vPeak  
        """
        saccade_L_df = pd.read_csv(f'{self.eyedir}/{sid}L_Saccade.csv')
        saccade_R_df = pd.read_csv(f'{self.eyedir}/{sid}R_Saccade.csv')
        saccade_df = pd.concat([saccade_L_df, saccade_R_df], ignore_index=True)
        # first assign trial number if tStart and tEnd 
        # are within trial_start and trial_end in trial_event_df
        # Discard rows that are not within any trial
        saccade_df['trial_no'] = None
        for _, row in trial_event_df.iterrows():
            if row['trial_start'] is not None:
                saccade_df.loc[(saccade_df['tStart'] >= row['trial_start']) & (saccade_df['tEnd'] <= row['trial_end']), 'trial_no'] = row['trial_no']
        saccade_df = saccade_df.dropna(subset=['trial_no'])
        # print(saccade_df)

        # Initialize empty DataFrames for each phase
        saccade_fix_df = pd.DataFrame()
        saccade_stim_df = pd.DataFrame()
        saccade_resp_df = pd.DataFrame()

        for _, row in trial_event_df.iterrows():

            # Filter by fixation start and end
            # Note: if there is a fix_succeed timestamp, use the 1-s period before it as fix_start
            # Data is recorded at 250 Hz
            # Because this means subject failed fixation and entered 'fixation helper'
            # These saccades we're not interested in
            if row['fix_start'] is not None and row['fix_end'] is not None:
                # Use fix_succeed as fix_start if it exists
                fix_start = row['fix_start'] if row['fix_failed'] is None else row['fix_succeed'] - 250
                filtered = saccade_df.loc[
                    (saccade_df['tStart'] >= fix_start) & 
                    (saccade_df['tEnd'] <= row['fix_end'])
                ].copy()  # Make a copy to avoid modifying the original DataFrame
                filtered['phase'] = 'Fixation'
                saccade_fix_df = pd.concat([saccade_fix_df, filtered], ignore_index=True)
            
            # Filter by stimulus start and end
            if row['stim_start'] is not None and row['stim_end'] is not None:
                filtered = saccade_df.loc[
                    (saccade_df['tStart'] >= row['stim_start']) & 
                    (saccade_df['tEnd'] <= row['stim_end'])
                ].copy()
                filtered['phase'] = 'Stimulus'
                saccade_stim_df = pd.concat([saccade_stim_df, filtered], ignore_index=True)
            
            # Filter by response start and end
            if row['resp_start'] is not None and row['resp_end'] is not None:
                filtered = saccade_df.loc[
                    (saccade_df['tStart'] >= row['resp_start']) & 
                    (saccade_df['tEnd'] <= row['resp_end'])
                ].copy()
                filtered['phase'] = 'Response'
                saccade_resp_df = pd.concat([saccade_resp_df, filtered], ignore_index=True)

        # print(saccade_fix_df.head())
        # print(saccade_stim_df.head())
        # print(saccade_resp_df.head())

        # saccade_phase_df = pd.concat([saccade_fix_df, saccade_stim_df, saccade_resp_df], ignore_index=True)
        saccade_phase_df = pd.concat([saccade_fix_df, saccade_stim_df], ignore_index=True)

        saccade_summary = saccade_phase_df.groupby(['phase', 'eye', 'trial_no']).agg({
                                                'ampDeg': ['mean', 'max'],
                                                'vPeak': ['mean', 'max'],
                                                'duration': 'mean'
                                            }).reset_index()

        # Flatten multi-level column names created by aggregation
        saccade_summary.columns = [
            'phase', 'eye', 'trial_no', 
            'saccade_amplitude_mean', 'saccade_amplitude_max', 
            'saccade_velocity_mean', 'saccade_velocity_max', 
            'saccade_duration_mean'
        ]
        # print(saccade_summary)


        return saccade_df, saccade_phase_df, saccade_summary

    def fixation_by_trial(self, sid, trial_event_df):
        """
        Columnes: eye, tStart, tEnd, duration, xAvg, yAvg, pupilAvg
        """
        fixation_L_df = pd.read_csv(f'{self.eyedir}/{sid}L_Fixation.csv')
        fixation_R_df = pd.read_csv(f'{self.eyedir}/{sid}R_Fixation.csv')
        fixation_df = pd.concat([fixation_L_df, fixation_R_df], ignore_index=True)
        # first assign trial number if tStart and tEnd 
        # are within trial_start and trial_end in trial_event_df
        # Discard rows that are not within any trial
        fixation_df['trial_no'] = None
        for _, row in trial_event_df.iterrows():
            if row['trial_start'] is not None:
                fixation_df.loc[(fixation_df['tStart'] >= row['trial_start']) & (fixation_df['tEnd'] <= row['trial_end']), 'trial_no'] = row['trial_no']
        fixation_df = fixation_df.dropna(subset=['trial_no'])
        # print(fixation_df)

        # Initialize empty DataFrames for each phase
        fixation_fix_df = pd.DataFrame()
        fixation_stim_df = pd.DataFrame()
        fixation_resp_df = pd.DataFrame()

        for _, row in trial_event_df.iterrows():

            # Filter by fixation start and end
            # Note: if there is a fix_succeed timestamp, use the 1-s period before it as fix_start
            # Data is recorded at 250 Hz
            # Because this means subject failed fixation and entered 'fixation helper'
            # These saccades we're not interested in
            if row['fix_start'] is not None and row['fix_end'] is not None:
                # Use fix_succeed as fix_start if it exists
                fix_start = row['fix_start'] # if row['fix_failed'] is None else row['fix_succeed'] - 250
                filtered = fixation_df.loc[
                    (fixation_df['tStart'] >= fix_start) & 
                    (fixation_df['tEnd'] <= row['trial_end'])
                ].copy()
                filtered['phase'] = 'Fixation'
                fixation_fix_df = pd.concat([fixation_fix_df, filtered], ignore_index=True)

            # Filter by stimulus start and end
            if row['stim_start'] is not None and row['stim_end'] is not None:
                filtered = fixation_df.loc[
                    (fixation_df['tStart'] >= row['stim_start']) & 
                    (fixation_df['tEnd'] <= row['trial_end'])
                ].copy()
                filtered['phase'] = 'Stimulus'
                fixation_stim_df = pd.concat([fixation_stim_df, filtered], ignore_index=True)
            
            # Filter by response start and end
            if row['resp_start'] is not None and row['resp_end'] is not None:
                filtered = fixation_df.loc[
                    (fixation_df['tStart'] >= row['resp_start']) & 
                    (fixation_df['tEnd'] <= row['resp_end'])
                ].copy()
                filtered['phase'] = 'Response'
                fixation_resp_df = pd.concat([fixation_resp_df, filtered], ignore_index=True)
            
        # fixation_phase_df = pd.concat([fixation_fix_df, fixation_stim_df, fixation_resp_df], ignore_index=True)
        fixation_phase_df = pd.concat([fixation_fix_df, fixation_stim_df], ignore_index=True)


        fixation_summary = fixation_phase_df.groupby(['phase', 'eye', 'trial_no']).agg({
                                                'xAvg': ['mean', 'max'],
                                                'yAvg': ['mean', 'max'],
                                                'pupilAvg': ['mean', 'max'],
                                                'duration': 'mean'
                                            }).reset_index()

        # Flatten multi-level column names created by aggregation
        fixation_summary.columns = [
            'phase', 'eye', 'trial_no', 
            'fixation_x_mean', 'fixation_x_max', 
            'fixation_y_mean', 'fixation_y_max',
            'pupil_avg_mean', 'pupil_avg_max', 
            'fixation_duration_mean'
        ]
        # print(fixation_summary)

        return fixation_df, fixation_phase_df, fixation_summary

