# Overleaf teaching document

Upload **offgrid_multi_gfm_teaching.tex** to a blank Overleaf project and select it as the main document. Use **pdfLaTeX**, then Recompile. The `.tex` file is standalone: no external images, `.bib` file, shell escape, or Python execution is required.

You can also upload **offgrid_multi_gfm_overleaf.zip** using Overleaf's New Project → Upload Project option.

The document includes a physical-system diagram, problem formulation, staged control solutions, equations and units, worked examples, corresponding solver excerpts, numerical integration, analytical checks, model limitations, and exercises with suggested answers. References are embedded in the source.

The document describes the actual reduced model and identifies what would require a more complete network/converter simulation.

For maintenance only: `build_teaching_document.py` combines `preamble.part`, the maintained `../control-system.md`, and `closing.part` into the standalone `.tex`. Overleaf does not need these build inputs. If regenerating, run the build script with Python and then recheck compilation.
