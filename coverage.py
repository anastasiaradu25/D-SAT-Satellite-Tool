import numpy as np
import pandas as pd
from link_budget import link_budget_from_range

def add_link_budget_columns(geometry_df,cfg,min_elevation_deg):
    df=geometry_df.copy(); b=pd.DataFrame(list(df['range_km'].apply(lambda d: link_budget_from_range(float(d),cfg))),index=df.index)
    for c in b.columns: df[c]=b[c]
    df['above_min_elevation']=df['elevation_deg']>=float(min_elevation_deg)
    df['positive_margin']=df['margin_db']>0
    df['link_available']=df['above_min_elevation'] & df['positive_margin']
    return df

def combine_constellation(df):
    if df.empty: return df.copy()
    idx=df.groupby(['time_utc','point'])['margin_db'].idxmax()
    best=df.loc[idx].copy().sort_values(['time_utc','point'])
    anylink=df.groupby(['time_utc','point'])['link_available'].any().rename('constellation_link').reset_index()
    best=best.merge(anylink,on=['time_utc','point'],how='left'); best['link_available']=best['constellation_link']; best.drop(columns=['constellation_link'],inplace=True)
    return best

def coverage_over_time(df):
    if df.empty: return pd.DataFrame()
    o=df.groupby('time_utc')['link_available'].agg(['sum','count']).reset_index(); o.rename(columns={'sum':'covered_points','count':'total_points'},inplace=True); o['coverage_pct']=100*o['covered_points']/o['total_points']; return o

def _extract(g,step_seconds):
    g=g.sort_values('time_utc').copy(); active=g['link_available'].astype(bool).to_numpy(); times=pd.to_datetime(g['time_utc'],utc=True).tolist(); out=[]; start=None
    for i,on in enumerate(active):
        if on and start is None: start=i
        last=i==len(active)-1
        if start is not None and ((not on) or last):
            end=i if on and last else i-1; seg=g.iloc[start:end+1]
            out.append({'start_utc':times[start],'end_utc':times[end],'duration_min':max(step_seconds,int((times[end]-times[start]).total_seconds())+step_seconds)/60,'max_elevation_deg':float(seg['elevation_deg'].max()),'min_range_km':float(seg['range_km'].min()),'max_margin_db':float(seg['margin_db'].max())}); start=None
    return out

def pass_table(df,step_seconds):
    rows=[]
    for point,g in df.groupby('point'):
        prev=None
        for n,p in enumerate(_extract(g,step_seconds),1):
            rev=np.nan if prev is None else (p['start_utc']-prev).total_seconds()/60
            rows.append({'point':point,'pass_number':n,**p,'revisit_from_prev_min':rev}); prev=p['end_utc']
    return pd.DataFrame(rows)

def point_statistics(df,passes_df,step_seconds,data_rate_bps):
    if df.empty: return pd.DataFrame()
    dur=(df['time_utc'].max()-df['time_utc'].min()).total_seconds()/3600
    rows=[]
    for point,g in df.groupby('point'):
        active=int(g['link_available'].sum()); contact=active*step_seconds; pp=passes_df[passes_df['point']==point] if not passes_df.empty else pd.DataFrame(); r=pp['revisit_from_prev_min'].dropna() if not pp.empty else pd.Series(dtype=float)
        rows.append({'point':point,'simulation_hours':dur,'contact_time_min':contact/60,'contact_fraction_pct':100*active/max(len(g),1),'number_of_passes':len(pp),'mean_revisit_min':float(r.mean()) if len(r) else np.nan,'max_revisit_min':float(r.max()) if len(r) else np.nan,'estimated_data_volume_MB':(contact*data_rate_bps/8)/1e6})
    return pd.DataFrame(rows)
