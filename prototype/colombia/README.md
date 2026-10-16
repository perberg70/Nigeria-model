# Colombia prototype

This folder holds the Colombia decision-support prototype, the counterpart of the Nigeria
prototype in `prototype/africa-prototype.html`.

**Status:** placeholder. No prototype file has been added yet, and nothing for Colombia is
published.

## Publishing on GitHub Pages

The workflow `.github/workflows/deploy-pages.yml` is already wired for this folder:

1. Add the prototype as a single self-contained file named `colombia-prototype.html` in this
   folder.
2. Add a link to `colombia/` in `site/index.html`, beside the Nigeria link.
3. Merge to `main`. A push that touches this folder triggers the workflow, which copies the file
   to `_site/colombia/index.html`. If the file is absent, the step is skipped and the rest of the
   site deploys unchanged.

The public link will be `https://perberg70.github.io/Nigeria-model/colombia/`.

The site is public: check the embedded model content and source-data licences before merging.

## Data and code

The Colombia modelling work so far is documented in the MSc-thesis repository
(`03_models/*colombia*` memos). When Colombia data and scripts are added here, follow
`AGENTS.md`: region-specific values go in configuration or data files, not in Python logic, and
proxied or transferred values are flagged.
