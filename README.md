# Off-grid multi-GFM PCS environment

Interactive workbench for studying off-grid parallel grid-forming battery PCSs, frequency control, EMS power sharing, SoC balancing and voltage coordination.

## Run online — no installation required

**[Launch the off-grid multi-GFM workbench](https://offgridmultigfm.streamlit.app/)**

1. Open the app and click **Run simulation** to explore the default three-PCS scenario.
2. Adjust the parameters or upload a load CSV, then run another scenario to compare results.
3. Open **Control system explained** for the teaching guide, equations and Python walkthrough.
4. Use **Source & downloads** to inspect the implementation and export results.

This is a reduced-order teaching and exploratory model. All units share one frequency state; voltage and circulating current are estimates. See [model assumptions](docs/model-notes.md) before interpreting results. Session scenarios are temporary; download runs you want to keep.

## Run locally

This project is independent of DoubleConversionBESSforAIDataCenter.

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

Default load scenario: 3 MW initially, 6 MW at 1 s, 4 MW at 3 s, 5.5 MW at 5.5 s; finish at 8 s. A fixed random seed makes voltage mismatches repeatable. Battery energy defaults to an accelerated 30 MJ per unit so SoC dynamics are visible over the demonstration interval; use the intended battery capacity for engineering studies.

See [model notes](docs/model-notes.md) for the implemented equations, assumptions and engineering scope. The [online workbench](https://offgridmultigfm.streamlit.app/) uses the same solver and interface as the local application.

## Teaching guide

Read the [control-system explanation](docs/control-system.md), [model assumptions](docs/model-notes.md), or the detailed [LaTeX teaching document](docs/overleaf/offgrid_multi_gfm_teaching.tex). For Overleaf, upload the [standalone project ZIP](docs/overleaf/offgrid_multi_gfm_overleaf.zip) or use the [LaTeX source](docs/overleaf/offgrid_multi_gfm_teaching.tex).

## Tests and cloud entry point

Run `python -m pytest` in the activated environment. The suite covers equilibrium, load steps, power saturation, SoC protection, variable PCS count and the dashboard Run flow.

For Streamlit Community Cloud, select `cloud/streamlit_app.py` as the main file and Python 3.12. Its adjacent `cloud/requirements.txt` installs the web dependencies. The cloud entry point loads the same solver and interface as the local app. This repository does not require API keys. GitHub publication alone does not deploy a hosted app.

The virtual environment and generated simulation outputs are excluded from version control. The local batch launcher requires an existing `.venv`; for a fresh checkout, follow the Conda setup above.
