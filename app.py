from datetime import datetime,date,time,timezone
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from shapely.geometry import Point,Polygon
from data import ROMANIA_CITIES,DEFAULT_TLE,ROMANIA_APPROX_POLYGON
from orbit import GroundPoint,build_satellites,make_utc_datetimes,geometry_for_points
from link_budget import RadioConfig,validation_case
from coverage import add_link_budget_columns,combine_constellation,coverage_over_time,pass_table,point_statistics

st.set_page_config(page_title='D-SAT Link Budget & Coverage',layout='wide')
st.title('🛰️ D-SAT Link Budget & Constellation Coverage Tool')
st.caption('TLE/SGP4 → Range & Elevation → FSPL → C/N₀ → Eb/N₀ → Link Margin → Coverage & Revisit')

@st.cache_data(show_spinner=False)
def build_grid(step_deg):
    poly=Polygon(ROMANIA_APPROX_POLYGON); minx,miny,maxx,maxy=poly.bounds; pts=[]; n=1; lat=miny
    while lat<=maxy+1e-9:
        lon=minx
        while lon<=maxx+1e-9:
            if poly.contains(Point(lon,lat)) or poly.touches(Point(lon,lat)):
                pts.append(GroundPoint(f'GRID-{n:03d}',lat,lon)); n+=1
            lon+=step_deg
        lat+=step_deg
    return pts

@st.cache_data(show_spinner=False)
def simulate_cached(tle_text,start_iso,duration_hours,step_seconds,points_tuple,radio_tuple,min_elevation_deg):
    ts,sats=build_satellites(tle_text); start=datetime.fromisoformat(start_iso); times=make_utc_datetimes(start,duration_hours,step_seconds); pts=[GroundPoint(*p) for p in points_tuple]
    cfg=RadioConfig(frequency_mhz=radio_tuple[0],tx_power_w=radio_tuple[1],tx_gain_dbi=radio_tuple[2],tx_line_loss_db=radio_tuple[3],pointing_loss_db=radio_tuple[4],polarization_loss_db=radio_tuple[5],atmospheric_loss_db=radio_tuple[6],data_rate_bps=radio_tuple[7],required_ebn0_db=radio_tuple[8],rx_gain_dbi=radio_tuple[9],system_noise_temp_k=radio_tuple[10])
    geom=geometry_for_points(sats,ts,times,pts); full=add_link_budget_columns(geom,cfg,min_elevation_deg); combined=combine_constellation(full); cov=coverage_over_time(combined); passes=pass_table(combined,step_seconds); stats=point_statistics(combined,passes,step_seconds,cfg.data_rate_bps); return full,combined,cov,passes,stats

st.sidebar.header('1) TLE / Constellation')
tle_text=st.sidebar.text_area('TLE(s)',DEFAULT_TLE,height=150)
st.sidebar.header('2) Simulation')
sim_date=st.sidebar.date_input('Start date (UTC)',date(2026,8,24)); sim_time=st.sidebar.time_input('Start time (UTC)',time(0,0)); duration_hours=st.sidebar.number_input('Duration [hours]',0.25,168.0,24.0,0.25); step_seconds=st.sidebar.selectbox('Time step',[10,30,60,120,300],index=2,format_func=lambda x:f'{x} s'); min_elevation_deg=st.sidebar.slider('Minimum elevation [deg]',0.0,30.0,10.0,1.0)
st.sidebar.header('3) Ground points'); ground_mode=st.sidebar.radio('Coverage points',['Romanian cities','Approx. Romania grid']); grid_step=0.75
if ground_mode=='Approx. Romania grid': grid_step=st.sidebar.select_slider('Grid spacing [deg]',[1.0,0.75,0.5,0.35,0.25],value=0.75)
st.sidebar.header('4) Radio parameters')
frequency_mhz=st.sidebar.number_input('Frequency [MHz]',value=437.5,min_value=1.0); tx_power_w=st.sidebar.number_input('Tx power [W]',value=1.0,min_value=0.001,format='%.3f'); tx_gain_dbi=st.sidebar.number_input('Tx antenna gain [dBi]',value=0.4); rx_gain_dbi=st.sidebar.number_input('Rx antenna gain [dBi]',value=17.6); system_noise_temp_k=st.sidebar.number_input('System noise temperature [K]',value=630.96,min_value=1.0); data_rate_bps=st.sidebar.number_input('Data rate [bps]',value=4800.0,min_value=1.0)
with st.sidebar.expander('Losses & required Eb/N0'):
    tx_line_loss_db=st.number_input('Tx line loss [dB]',value=1.7); pointing_loss_db=st.number_input('Pointing loss [dB]',value=3.0); polarization_loss_db=st.number_input('Polarization loss [dB]',value=3.0); atmospheric_loss_db=st.number_input('Atmospheric loss [dB]',value=1.8); required_ebn0_db=st.number_input('Required Eb/N0 [dB]',value=13.5)
cfg=RadioConfig(frequency_mhz,tx_power_w,tx_gain_dbi,tx_line_loss_db,pointing_loss_db,polarization_loss_db,atmospheric_loss_db,data_rate_bps,required_ebn0_db,rx_gain_dbi,system_noise_temp_k)
st.sidebar.metric('Calculated G/T',f'{cfg.g_over_t_dbk:.2f} dB/K'); st.sidebar.metric('EIRP',f'{cfg.eirp_dbw:.2f} dBW')
start_dt=datetime.combine(sim_date,sim_time,tzinfo=timezone.utc); points=ROMANIA_CITIES if ground_mode=='Romanian cities' else build_grid(float(grid_step)); points_tuple=tuple((p.name,p.lat_deg,p.lon_deg,p.elevation_m) for p in points); radio_tuple=(frequency_mhz,tx_power_w,tx_gain_dbi,tx_line_loss_db,pointing_loss_db,polarization_loss_db,atmospheric_loss_db,data_rate_bps,required_ebn0_db,rx_gain_dbi,system_noise_temp_k)
run=st.sidebar.button('▶ Run simulation',type='primary',use_container_width=True)

tab0,tab1,tab2,tab3,tab4,tab5=st.tabs(['Validation','Simulation','Passes','Coverage','Raw data','Equations'])
with tab0:
    st.subheader('Published D-SAT validation case'); v=validation_case(cfg); c1,c2,c3,c4=st.columns(4); c1.metric('Range','909.5 km'); c2.metric('Elevation','30°'); c3.metric('Calculated FSPL',f"{v['fspl_db']:.2f} dB",f"{v['fspl_db']-v['published_fspl_db']:+.2f} dB vs published"); c4.metric('Calculated margin',f"{v['margin_db']:.2f} dB",f"{v['margin_db']-v['published_margin_db']:+.2f} dB vs published")
    comp=pd.DataFrame({'Metric':['FSPL [dB]','Eb/N0 [dB]','Link margin [dB]'],'Calculated':[v['fspl_db'],v['ebn0_db'],v['margin_db']],'Published':[v['published_fspl_db'],v['published_ebn0_db'],v['published_margin_db']]}); comp['Difference']=comp['Calculated']-comp['Published']; st.dataframe(comp,use_container_width=True,hide_index=True)
if run:
    try:
        with st.spinner('Propagating TLE(s) and computing geometry + link budget...'):
            st.session_state['sim']=simulate_cached(tle_text,start_dt.isoformat(),float(duration_hours),int(step_seconds),points_tuple,radio_tuple,float(min_elevation_deg))
    except Exception as e: st.error(f'Simulation failed: {e}')
sim=st.session_state.get('sim')
with tab1:
    st.subheader('Time-dependent geometry and link budget')
    if sim is None: st.warning('Click Run simulation.')
    else:
        full,combined,cov,passes,stats=sim; sats=sorted(full['satellite'].unique()); pts=sorted(full['point'].unique()); c1,c2,c3,c4=st.columns(4); c1.metric('Satellites',len(sats)); c2.metric('Ground points',len(pts)); c3.metric('Rows computed',f'{len(full):,}'); c4.metric('Maximum margin',f"{full['margin_db'].max():.1f} dB")
        pchoice=st.selectbox('Inspect point',pts); schoice=st.selectbox('Inspect satellite',sats); view=full[(full.point==pchoice)&(full.satellite==schoice)]
        f1=px.line(view,x='time_utc',y='elevation_deg',title=f'Elevation – {schoice} / {pchoice}'); f1.add_hline(y=min_elevation_deg,line_dash='dash'); st.plotly_chart(f1,use_container_width=True)
        st.plotly_chart(px.line(view,x='time_utc',y='range_km',title='Slant range'),use_container_width=True)
        f3=px.line(view,x='time_utc',y='margin_db',title='Link margin'); f3.add_hline(y=0,line_dash='dash'); st.plotly_chart(f3,use_container_width=True)
with tab2:
    st.subheader('Passes and revisit time')
    if sim is None: st.warning('Run the simulation first.')
    else:
        full,combined,cov,passes,stats=sim
        if passes.empty: st.warning('No valid passes found.')
        else: st.dataframe(passes,use_container_width=True,hide_index=True); st.download_button('Download passes CSV',passes.to_csv(index=False).encode(),file_name='passes.csv',mime='text/csv')
        st.subheader('Per-point summary'); st.dataframe(stats,use_container_width=True,hide_index=True)
with tab3:
    st.subheader('Constellation coverage')
    if sim is None: st.warning('Run the simulation first.')
    else:
        full,combined,cov,passes,stats=sim; c1,c2,c3=st.columns(3); c1.metric('Mean coverage',f"{cov['coverage_pct'].mean():.1f}%"); c2.metric('Maximum coverage',f"{cov['coverage_pct'].max():.1f}%"); c3.metric('Points',combined['point'].nunique()); st.plotly_chart(px.line(cov,x='time_utc',y='coverage_pct',title='Coverage vs time',range_y=[0,100]),use_container_width=True)
        bt=cov.loc[cov['coverage_pct'].idxmax(),'time_utc']; snap=combined[combined.time_utc==bt].copy(); snap['status']=np.where(snap.link_available,'Covered','Not covered'); fig=px.scatter_map(snap,lat='lat_deg',lon='lon_deg',color='status',hover_name='point',hover_data=['satellite','elevation_deg','range_km','margin_db'],zoom=5,height=650,title=f'Best coverage snapshot: {bt}'); st.plotly_chart(fig,use_container_width=True)
        st.caption('City mode = fraction of selected points, not area. Grid mode = approximate area-style metric based on a coarse offline Romania polygon.')
with tab4:
    st.subheader('Raw calculated data')
    if sim is None: st.warning('Run the simulation first.')
    else:
        full,combined,cov,passes,stats=sim; st.dataframe(full.head(5000),use_container_width=True,hide_index=True); st.download_button('Download all raw data CSV',full.to_csv(index=False).encode(),file_name='dsat_link_budget_raw.csv',mime='text/csv')
with tab5:
    st.subheader('Equations used'); st.latex(r'P_t[dBW]=10\log_{10}(P_t[W])'); st.latex(r'EIRP=P_t+G_t-L_{line}'); st.latex(r'FSPL=32.44+20\log_{10}(d_{km})+20\log_{10}(f_{MHz})'); st.latex(r'G/T=G_r-10\log_{10}(T_{sys})'); st.latex(r'C/N_0=P_t+G_t-L_{line}-L_{point}-FSPL-L_{pol}-L_{atm}+G/T+228.6'); st.latex(r'E_b/N_0=C/N_0-10\log_{10}(R_b)'); st.latex(r'Margin=(E_b/N_0)_{available}-(E_b/N_0)_{required}'); st.latex(r'LINK=(Elevation\ge Elevation_{min})\land(Margin>0)')
