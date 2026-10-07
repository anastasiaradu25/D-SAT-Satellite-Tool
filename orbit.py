from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from skyfield.api import EarthSatellite, load, wgs84

@dataclass(frozen=True)
class GroundPoint:
    name: str
    lat_deg: float
    lon_deg: float
    elevation_m: float = 0.0

def parse_tle_text(text):
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    if len(lines)<2: raise ValueError('TLE text must contain at least 2 lines')
    out=[]; i=0; n=1
    while i<len(lines):
        if lines[i].startswith('1 ') and i+1<len(lines) and lines[i+1].startswith('2 '):
            out.append((f'SAT-{n}',lines[i],lines[i+1])); n+=1; i+=2
        elif i+2<len(lines) and lines[i+1].startswith('1 ') and lines[i+2].startswith('2 '):
            out.append((lines[i],lines[i+1],lines[i+2])); i+=3
        else: raise ValueError(f'Cannot parse TLE near: {lines[i]}')
    return out

def build_satellites(tle_text):
    ts=load.timescale(); sats=[]
    for name,l1,l2 in parse_tle_text(tle_text): sats.append(EarthSatellite(l1,l2,name,ts))
    return ts,sats

def make_utc_datetimes(start_utc,duration_hours,step_seconds):
    if start_utc.tzinfo is None: start_utc=start_utc.replace(tzinfo=timezone.utc)
    else: start_utc=start_utc.astimezone(timezone.utc)
    total=int(round(duration_hours*3600))
    return [start_utc+pd.Timedelta(seconds=int(s)) for s in np.arange(0,total+1,step_seconds,dtype=int)]

def geometry_for_points(satellites,ts,datetimes_utc,points):
    t=ts.from_datetimes(datetimes_utc); frames=[]
    for sat in satellites:
        for p in points:
            station=wgs84.latlon(latitude_degrees=p.lat_deg,longitude_degrees=p.lon_deg,elevation_m=p.elevation_m)
            topo=(sat-station).at(t)
            alt,az,distance=topo.altaz()
            frames.append(pd.DataFrame({'time_utc':pd.to_datetime(datetimes_utc,utc=True),'satellite':sat.name,'point':p.name,'lat_deg':p.lat_deg,'lon_deg':p.lon_deg,'elevation_deg':alt.degrees,'azimuth_deg':az.degrees,'range_km':distance.km}))
    return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()
