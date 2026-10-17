"""Run the screenshot load-step example from the command line."""
import argparse
from pathlib import Path
from .model import simulate
from .report import bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='outputs/latest')
    args = parser.parse_args()
    result = simulate([0, 1, 3, 5.5, 8], [3, 6, 4, 5.5, 5.5], initial_soc=[80, 60, 70])
    html, archive = bundle(result)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out/'report.html').write_text(html, encoding='utf-8')
    (out/'run.zip').write_bytes(archive)
    print(result['termination'])
    print(out.resolve())
