"""Splice the generated baseline blocks into the standalone prototype HTML."""

from __future__ import annotations

import os
from pathlib import Path

from .js_block import BLOCK1, BLOCK2, BLOCK3, BLOCK4


def replace_fragment(text: str, start_marker: str, end_marker: str, fragment: str) -> str:
    """Replace one generated object fragment while preserving line indentation."""
    start = text.index(start_marker)
    line_start = text.rfind("\n", 0, start) + 1
    end = text.index(end_marker, start)
    return text[:line_start] + fragment.rstrip() + "\n\n" + text[end:]


def update_prototype_html(html: str, generated: str) -> str:
    """Return `html` with the four blocks of `generated` copied in.

    The anchors are text the prototype already carries, and each must occur exactly
    where the previous run left it: ``emissions:{`` up to ``  /* --- Social Cost of
    Carbon``; ``sspBaseline:{`` up to ``         totalEnergy2023TJ:``; ``popSSP:{`` up to
    ``         elasticityTotal:``; ``pollutingIdxSSP:{`` up to its closing ``\\n    },``.
    A missing anchor raises ValueError.
    """

    def fragment(marker, next_marker=None):
        start = generated.index(marker + "\n") + len(marker + "\n")
        end = generated.index(next_marker, start) if next_marker else len(generated)
        return generated[start:end].strip("\r\n")

    html = replace_fragment(
        html, "emissions:{", "  /* --- Social Cost of Carbon", fragment(BLOCK1, BLOCK2)
    )
    html = replace_fragment(
        html, "sspBaseline:{", "         totalEnergy2023TJ:", fragment(BLOCK2, BLOCK3)
    )
    html = replace_fragment(html, "popSSP:{", "         elasticityTotal:", fragment(BLOCK3, BLOCK4))
    # BLOCK 4 ends at its OWN closing brace, not at a comment, because the prototype carries no
    # comments to anchor on.
    if "pollutingIdxSSP:{" not in html:
        raise ValueError("prototype has no pollutingIdxSSP block")
    start = html.index("pollutingIdxSSP:{")
    line_start = html.rfind("\n", 0, start) + 1
    close = html.index("\n    },", start) + len("\n    },")
    return html[:line_start] + fragment(BLOCK4).rstrip() + html[close:]


def write_prototype(path: Path, generated: str) -> None:
    """Splice `generated` into the prototype at `path`, replacing the file only on success.

    The new HTML is built in memory first and staged to ``<path>.tmp`` before
    os.replace, so a failed splice (a missing anchor) leaves the original untouched.
    """
    new_html = update_prototype_html(path.read_text(encoding="utf-8"), generated)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(new_html)
    os.replace(tmp, path)
