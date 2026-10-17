import numpy as np
import pytest
from offgrid_gfm.model import Config, simulate


def test_equilibrium():
    c = Config(soc_gain_w_pct=0, mismatch_pct=0)
    r = simulate([0, .2], [3, 3], c, [70]*3)
    d = r['columns']
    assert np.allclose(d['frequency_hz'], 60)
    assert np.allclose(d['total_mw'], 3)
    expected = 70 - 1e6*.2/(c.energy_mwh*3.6e9)*100
    assert d['pcs1_soc_pct'][-1] == pytest.approx(expected)
    assert np.max(d['circulating_a']) == 0


def test_load_step_and_rating():
    r = simulate([0,.1,.5], [3,30,30], Config(energy_mwh=1))
    d = r['columns']
    assert d['frequency_hz'][-1] < 60
    for i in range(1,4):
        assert np.max(d[f'pcs{i}_power_mw']) <= 5.16+1e-5


def test_protection_event():
    r = simulate([0,1], [3,3], Config(soc_gain_w_pct=0), [2.1]*3)
    assert 'protection' in r['termination']
    assert r['columns']['time_s'][-1] == pytest.approx(.03, abs=1e-5)
    assert r['columns']['pcs1_soc_pct'][-1] == pytest.approx(2)


def test_validation_and_variable_count():
    with pytest.raises(ValueError):
        Config(communication_tau_s=0)
    with pytest.raises(ValueError):
        simulate([0,0], [1,1])
    r = simulate([0,.1], [2,2], Config(units=2), [70,70])
    assert 'pcs2_power_mw' in r['columns']
    assert 'pcs3_power_mw' not in r['columns']


def test_reference_scenario():
    r = simulate([0,1,3,5.5,8], [3,6,4,5.5,5.5], initial_soc=[80,60,70])
    assert r['columns']['time_s'][-1] == pytest.approx(8)
    assert all(np.all(np.isfinite(v)) for v in r['columns'].values())
