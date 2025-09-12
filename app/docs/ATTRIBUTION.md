# Attribution

This project includes vocabulary lists from **“List of Dirty, Naughty, Obscene, and Otherwise Bad Words” (LDNOOBW)** by Shutterstock, licensed under **CC BY 4.0**.

- Upstream: https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words  
- License (legal code): https://creativecommons.org/licenses/by/4.0/legalcode  
- Local copy of the license: [`docs/licenses/CC-BY-4.0.txt`](../docs/licenses/CC-BY-4.0.txt)

## Snapshot reference
- LDNOOBW commit: `5faf2ba42d7b1c0977169ec3611df25a3c08eb13` (2020-07-13)

## Modifications in KLKCHAN
We use the lists as a data source and apply the following processing for runtime filtering:
- Text normalization (lowercasing, accent stripping, basic leet mapping).
- Collapse of exaggerated repetitions (`"puuuta"` → `"puuta"`) and flexible spacing for multi-word entries.
- Regex compilation with word boundaries to reduce false positives.
- Multi-language merge (e.g., **es** + **en**) with caching.
- Overrides mechanism to **add/remove** terms without altering upstream (`app/data/ldnoobw/overrides.json`).
- Potentially a subset of languages (currently **es**, **en**) stored in:
  - `app/data/ldnoobw/es.txt`
  - `app/data/ldnoobw/en.txt`

> We may have modified/normalized the lists for KLKCHAN usage. See the source files above and our filtering code under `app/utils/banned_words.py`.
