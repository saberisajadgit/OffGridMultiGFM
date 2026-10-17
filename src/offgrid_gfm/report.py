"""Interactive plots and portable result exports."""
import csv
from io import StringIO, BytesIO
import json
from zipfile import ZipFile
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def report(result):
    d, n = result['columns'], result['config']['units']
    groups = [(['frequency_hz'], 'Frequency (Hz)'),
              (['load_mw', 'total_mw']+[f'pcs{i}_power_mw' for i in range(1,n+1)], 'Active power (MW)'),
              ([f'pcs{i}_soc_pct' for i in range(1,n+1)], 'Battery SoC (%)'),
              ([f'pcs{i}_reactive_mvar' for i in range(1,n+1)], 'Estimated reactive power (MVAr)'),
              ([f'pcs{i}_terminal_v' for i in range(1,n+1)], 'Estimated terminal phase voltage (V RMS)'),
              ([f'pcs{i}_secondary_mw' for i in range(1,n+1)], 'Secondary control (MW)'),
              (['compensation_v'], 'Voltage compensation norm (V)'),
              (['circulating_a'], 'Estimated circulating current (A)')]
    fig = make_subplots(rows=8, cols=1, shared_xaxes=True, vertical_spacing=.035, subplot_titles=[g[1] for g in groups])
    for row, (keys, _) in enumerate(groups, 1):
        for key in keys:
            fig.add_trace(go.Scatter(x=d['time_s'], y=d[key], name=key.replace('_', ' ')), row=row, col=1)
    fig.update_layout(height=1850, template='plotly_white', hovermode='x unified', title='Off-grid multi-GFM PCS cluster')
    fig.update_xaxes(title_text='Time (s)', row=8, col=1)
    return fig


def bundle(result):
    out = StringIO()
    keys = list(result['columns'])
    writer = csv.writer(out)
    writer.writerow(keys)
    writer.writerows(zip(*(result['columns'][k] for k in keys)))
    metadata = {k:v for k,v in result.items() if k != 'columns'}
    html = report(result).to_html(include_plotlyjs=True)
    buf = BytesIO()
    with ZipFile(buf, 'w') as z:
        z.writestr('results.csv', out.getvalue())
        z.writestr('run.json', json.dumps(metadata, indent=2))
        z.writestr('report.html', html)
    return html, buf.getvalue()
