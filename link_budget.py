from __future__ import annotations
import math
from dataclasses import dataclass

K_BOLTZMANN_DBW_PER_K_HZ = -228.6

@dataclass
class RadioConfig:
    frequency_mhz: float = 437.5
    tx_power_w: float = 1.0
    tx_gain_dbi: float = 0.4
    tx_line_loss_db: float = 1.7
    pointing_loss_db: float = 3.0
    polarization_loss_db: float = 3.0
    atmospheric_loss_db: float = 1.8
    data_rate_bps: float = 4800.0
    required_ebn0_db: float = 13.5
    rx_gain_dbi: float = 17.6
    system_noise_temp_k: float = 630.957344480193

    @property
    def tx_power_dbw(self): return 10.0*math.log10(self.tx_power_w)
    @property
    def eirp_dbw(self): return self.tx_power_dbw+self.tx_gain_dbi-self.tx_line_loss_db
    @property
    def g_over_t_dbk(self): return self.rx_gain_dbi-10.0*math.log10(self.system_noise_temp_k)
    @property
    def bitrate_term_db(self): return 10.0*math.log10(self.data_rate_bps)

def fspl_db(range_km, frequency_mhz):
    if range_km <= 0 or frequency_mhz <= 0: raise ValueError('Range and frequency must be > 0')
    return 32.44+20*math.log10(range_km)+20*math.log10(frequency_mhz)

def link_budget_from_range(range_km, cfg):
    fspl=fspl_db(range_km,cfg.frequency_mhz)
    cn0=(cfg.tx_power_dbw+cfg.tx_gain_dbi-cfg.tx_line_loss_db-cfg.pointing_loss_db-fspl-cfg.polarization_loss_db-cfg.atmospheric_loss_db+cfg.g_over_t_dbk+228.6)
    ebn0=cn0-cfg.bitrate_term_db
    margin=ebn0-cfg.required_ebn0_db
    crx=cfg.eirp_dbw-cfg.pointing_loss_db-fspl-cfg.polarization_loss_db-cfg.atmospheric_loss_db+cfg.rx_gain_dbi
    n0=K_BOLTZMANN_DBW_PER_K_HZ+10*math.log10(cfg.system_noise_temp_k)
    return {'tx_power_dbw':cfg.tx_power_dbw,'eirp_dbw':cfg.eirp_dbw,'fspl_db':fspl,'g_over_t_dbk':cfg.g_over_t_dbk,'received_carrier_dbw':crx,'noise_density_dbw_hz':n0,'cn0_dbhz':cn0,'ebn0_db':ebn0,'margin_db':margin}

def validation_case(cfg=None):
    cfg=cfg or RadioConfig()
    d=link_budget_from_range(909.5,cfg)
    d.update({'range_km':909.5,'elevation_deg':30.0,'published_fspl_db':144.4,'published_ebn0_db':28.3,'published_margin_db':14.8})
    return d
