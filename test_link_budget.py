from link_budget import RadioConfig,validation_case,fspl_db
def test_fspl_validation(): assert abs(fspl_db(909.5,437.5)-144.4)<0.1
def test_default_gt(): assert abs(RadioConfig().g_over_t_dbk+10.4)<0.05
def test_validation_margin_close(): assert abs(validation_case()['margin_db']-14.35)<0.2
