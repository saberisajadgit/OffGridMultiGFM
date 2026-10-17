# Off-grid multi-GFM PCS environment

Independent sibling of DoubleConversionBESSforAIDataCenter. The existing project is unchanged.

In Anaconda Prompt:

```bat
cd /d C:\Users\saber\Documents\Python\PCSSimulation\OffGridMultiGFM
conda env create -f environment.yml
conda activate offgrid-multi-gfm
python -m pytest
python -m streamlit run app.py --server.port 8502
```

Alternatively use the local virtual environment if dependencies were installed:

```bat
.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

Command-line reference scenario: `offgrid-gfm --output outputs/latest`. Open outputs/latest/report.html or extract run.zip for CSV and metadata.

The workbench supports 2–12 equal-rated units (three by default), separate initial SoCs, editable ratings/controllers/impedance, step or linear CSV input (`time_s,load_mw`), eight interactive result panels, four session scenarios, source inspection and portable exports. Positive power means battery discharge; negative load means charging. Values shown under results belong to the selected completed run. Initial SoCs must be entered for every unit.

Screenshot reference load: 3 MW initially, 6 MW at 1 s, 4 MW at 3 s, 5.5 MW at 5.5 s; finish at 8 s. The screenshot seed and voltage mismatches are retained. Battery energy defaults to the screenshot's accelerated 30 MJ per unit, not a commercial battery size.

See [model notes](docs/model-notes.md) for deliberate departures from the source screenshots and the model's engineering scope. No cloud deployment is performed. A cloud entry point is supplied for later use.

## Teaching guide

Read the [control-system explanation](docs/control-system.md), [model assumptions](docs/model-notes.md), or the detailed [PDF teaching document](docs/overleaf/offgrid_multi_gfm_teaching.pdf). For Overleaf, upload the [standalone project ZIP](docs/overleaf/offgrid_multi_gfm_overleaf.zip) or use the [LaTeX source](docs/overleaf/offgrid_multi_gfm_teaching.tex).

## Tests and cloud entry point

Run `python -m pytest` in the activated environment. The suite covers equilibrium, load steps, power saturation, SoC protection, variable PCS count and the dashboard Run flow.

For Streamlit Community Cloud, select `cloud/streamlit_app.py` as the main file and Python 3.12. Its adjacent `cloud/requirements.txt` installs the web dependencies. The cloud entry point loads the same solver and interface as the local app. This repository does not require API keys. GitHub publication alone does not deploy a hosted app.

The virtual environment and generated simulation outputs are excluded from version control. The local batch launcher requires an existing `.venv`; for a fresh checkout, follow the Conda setup above.
