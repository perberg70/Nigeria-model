"""Extract numeric series from the vector charts of the Energy Transition Plan update.

One module per chart group: ``power`` (pp.17-18), ``demand`` (p.22), ``industry``
(pp.27-29) and ``cooking`` (pp.37-40). Each ``run(pdf, outdir)`` validates the
extraction against figures the document states in prose and writes nothing if
a gating check fails.
"""

from . import cooking, demand, industry, power
from .pdf_vectors import ExtractionError, parse_page, tokenize

CHARTS = {"power": power, "demand": demand, "cooking": cooking, "industry": industry}

__all__ = [
    "CHARTS",
    "ExtractionError",
    "cooking",
    "demand",
    "industry",
    "parse_page",
    "power",
    "tokenize",
]
