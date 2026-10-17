import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent/'src'))
from dataclasses import asdict
from io import StringIO
import json
import numpy as np
import streamlit as st
from offgrid_gfm.model import Config, simulate
from offgrid_gfm.report import report, bundle

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Off-grid Multi-GFM PCS', page_icon='⚡', layout='wide')
st.title('Off-grid multi-GFM PCS workbench')
st.write('Parallel battery PCS units form an islanded AC bus and share a changing load through droop, secondary control and EMS SoC balancing.')
st.caption('Reduced-order coherent-frequency model · No external grid · Positive PCS power discharges the batteries')
if 'runs' not in st.session_state:
    st.session_state.runs = []
with st.sidebar, st.form('setup'):
    st.subheader('Cluster setup')
    label = st.text_input('Scenario name', 'Three-PCS load steps')
    values = asdict(Config())
    values['units'] = st.number_input('PCS count', min_value=2, max_value=12, value=3)
    groups = {
        'Ratings & frequency': ['rating_mw','voltage_ll_v','frequency_hz','inertia_s','damping_pu','droop_fraction'],
        'EMS & battery': ['power_tau_s','communication_tau_s','secondary_w_hz_s','soc_gain_w_pct','energy_mwh','soc_min_pct','soc_max_pct'],
        'Voltage & impedance': ['mismatch_pct','transformer_r_pu','transformer_x_pu','virtual_r_pu','virtual_x_pu','q_droop_fraction','voltage_balance_gain_s'],
    }
    for group, fields in groups.items():
        with st.expander(group):
            for field in fields:
                values[field] = st.number_input(field, value=float(values[field]), format='%.6f')
    initial_text = st.text_input('Initial SoCs (%) — one per PCS', '80, 60, 70')
    upload = st.file_uploader('Optional load CSV: time_s,load_mw', type='csv')
    interpolation = st.selectbox('Load interpolation', ['step','linear'])
    run = st.form_submit_button('Run simulation', type='primary')

setup, controls, results, compare, equations, downloads = st.tabs(['System configuration','Control system explained','Simulation results','Compare scenarios','Model & equations','Source & downloads'])
with setup:
    st.subheader('Battery containers → parallel GFM PCSs → islanded AC bus → load')
    st.info('Default reference: 3 × 5.16 MW, 690 V L-L, 60 Hz; 3 → 6 → 4 → 5.5 MW at 0 / 1 / 3 / 5.5 s, ending at 8 s.')
    st.write('Each unit has a transformer and virtual impedance. The EMS adds SoC balancing to equal power sharing; local droop supplies fast response and secondary integral control restores frequency.')
    st.warning('The screenshot energy is only 30 MJ (0.00833 MWh) per unit and intentionally accelerates SoC dynamics. Set energy_mwh to the actual battery capacity for engineering studies.')
if run:
    try:
        c = Config(**values)
        soc = [float(v.strip()) for v in initial_text.split(',')]
        if upload:
            a = np.genfromtxt(StringIO(upload.getvalue().decode('utf-8-sig')), delimiter=',', names=True)
            t, p = a['time_s'], a['load_mw']
        else:
            t, p = [0,1,3,5.5,8], [3,6,4,5.5,5.5]
        with st.spinner('Solving cluster dynamics…'):
            result = simulate(t, p, c, soc, interpolation)
            html, archive = bundle(result)
        st.session_state.runs = (st.session_state.runs + [dict(name=label, result=result, html=html, archive=archive)])[-4:]
        st.success(result['termination'])
    except (ValueError, TypeError, KeyError, RuntimeError, UnicodeError) as exc:
        st.error(str(exc))
runs = st.session_state.runs
selected = st.selectbox('Completed scenario', range(len(runs)), format_func=lambda i: f'{i+1}. {runs[i]["name"]}') if runs else None
with results:
    if selected is None:
        st.info('Press Run simulation to generate the eight-panel dashboard.')
    else:
        record = runs[selected]
        d = record['result']['columns']
        st.caption(record['result']['termination'])
        a,b,c = st.columns(3)
        a.metric('Frequency minimum', f"{d['frequency_hz'].min():.3f} Hz")
        b.metric('Frequency maximum', f"{d['frequency_hz'].max():.3f} Hz")
        c.metric('Simulated through', f"{d['time_s'][-1]:.3f} s")
        st.plotly_chart(report(record['result']), width='stretch')
with compare:
    if len(runs) < 2:
        st.info('Run another scenario to compare frequency and settings.')
    else:
        import plotly.graph_objects as go
        fig = go.Figure()
        for record in runs:
            d = record['result']['columns']
            fig.add_trace(go.Scatter(x=d['time_s'], y=d['frequency_hz'], name=record['name']))
        st.plotly_chart(fig, width='stretch')
        st.dataframe([dict(scenario=r['name'], **r['result']['config'], initial_soc=r['result']['initial_soc'], interpolation=r['result']['interpolation']) for r in runs])
        st.caption('Overlays may use different loads and initial SoCs; inspect exported run data before attributing differences to control tuning.')
with controls:
    st.markdown((ROOT/'docs/control-system.md').read_text(encoding='utf-8'))
with equations:
    st.markdown((ROOT/'docs/model-notes.md').read_text(encoding='utf-8'))
with downloads:
    if selected is not None:
        record = runs[selected]
        st.download_button('HTML report', record['html'], 'offgrid-report.html', 'text/html')
        st.download_button('Run bundle (CSV + metadata + HTML)', record['archive'], 'offgrid-run.zip', 'application/zip')
    sources = sorted((ROOT/'src/offgrid_gfm').glob('*.py'))
    source = st.selectbox('Source file', sources, format_func=lambda p:p.name)
    st.code(source.read_text(encoding='utf-8'), language='python')
