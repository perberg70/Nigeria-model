# Codex repository instructions

## Project scope

This repository contains the data build and analysis code behind the Africa (Nigeria) energy,
emissions and climate-impact decision-support prototype (`prototype/africa-prototype.html`).
Its layout and rules follow the TRA420 Western Balkans model (`TRA420_Modeling_2025`): preserve
its config-driven, region-agnostic architecture.

## Operating principles

- Read relevant files before editing. Use repository search and Git history when the reason for existing behaviour is unclear.
- Make the smallest change that satisfies the task.
- Do not silently invent, interpolate, or substitute missing research data. Flag gaps explicitly in code, logs, configuration, or documentation.
- Keep modelling logic separate from thesis interpretation and user-interface presentation.
- Codex: do not edit `.claude/agents/`; those files are maintained with Claude Code. When a shared rule changes, update this file and the matching agent together (see `.codex/README.md`).

## Mandatory architecture checks

For changes to Python, YAML, configuration loading, demand equations, electrification, scenario data, or model documentation, apply the following checks:

1. **Explicit configuration**
   - Scripts under `scripts/` must require `--config` (`config_paths.add_config_argument`).
   - Read model inputs with `config_paths.require()` / `require_path()`; do not add hidden fallback values for required model inputs.

2. **Region-agnostic model logic**
   - Python model behaviour must not branch on hardcoded country or region names or ISO codes.
   - Country names may appear in tests, user-facing labels, documentation, and diagnostics when they do not control model logic.
   - Region-specific values belong in YAML or data files (`config.yaml`, `data/nigeria_regional_climate/admin1_units.yaml`).

3. **Scenario identity**
   - When combining Integrated Assessment Model data, identify scenarios by `(model, scenario)` pairs, not scenario name alone (`scenario_data.read_series`, `Marker.key`).

4. **Double-counting control**
   - When modifying demand, electrification, income elasticity, price elasticity, or total final energy calculations, identify whether the same effect is already represented elsewhere (e.g. the R10 efficiency residual removes the income effect the Burke & Csereklyei relation already applies).
   - Document the separation of effects before accepting a new term.

5. **Gap flagging**
   - Missing, proxied, transferred, interpolated, or assumed values must be visible and traceable.
   - Prefer an explicit warning, status field, provenance note, or validation error over silent completion.

## Generated files

- `data/scenario_compass_africa_r10/nigeria_baseline_block.js`, the four spliced blocks of `prototype/africa-prototype.html`, its `NIGERIA_ZONE_MAP` block (`scripts/build_zone_map.py`), the analysis reports (`*output*.txt`) and the ETP CSVs are outputs of `scripts/`. Regenerate them; never hand-edit them.
- A change that moves any committed output must regenerate and commit that output in the same change; the regression tests in `tests/` compare them byte for byte.
- The ETP CSVs are compared after line-ending normalisation: the extractors write CRLF while two committed files are stored with LF. Extract to a scratch `--output-dir` and keep the committed files unless the change is meant to move them (`data/seforall_nigeria_etp/README.md`).
- `docs/ssp_baseline.md` lists the prototype data that are still hand-pasted; keep them consistent by hand or extend the splice.

## Validation

- Run the narrowest relevant tests first.
- Use `pytest --basetemp=./.pytest_tmp <args>` rather than bare `pytest`; add `-m "not network"` offline.
- For Python syntax checks, use `python -m py_compile` on changed files when appropriate.
- Run `ruff check .` and `ruff format --check .` (settings identical to TRA420's, pinned to ruff 0.6.9 in `.pre-commit-config.yaml`).
- Report environment failures separately from model or logic failures.

## Research and documentation checks

For Markdown reports, thesis material, and research notes:

- Source externally derived numeric claims with a source and data year near the first relevant use.
- Do not demand citations for equation numbers, section numbers, sample identifiers, or clearly labelled model outputs.
- Distinguish external facts, calculated results, assumptions, methodological constants, and examples.
- Mark geographic, temporal, and methodological mismatches explicitly (e.g. IMAGE Africa R10 used for Nigeria, cross-country elasticities transferred to Nigeria).
- Verify claims about repository behaviour against the current code or configuration.

## Reusable Codex review prompts

Task-specific review instructions are stored in `.codex/prompts/`:

- `explore.md`
- `config-guard.md`
- `gap-flagger.md`
- `source-checker.md`
- `test-runner.md`

Use the relevant prompt as a task checklist. These are reusable Codex prompts, not automatically spawned sub-agents.
