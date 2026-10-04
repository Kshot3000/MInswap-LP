# Bugs Fixed

## Original issues addressed
- Invalid identifier `MIN SWAP_FEE` → renamed to `MINSWAP_FEE`
- Used float for financial calculations → switched to `Decimal` for precision
- No mock mode for local development → added `MOCK_MODE` when API key missing
- `is_swap_tx` always returned True → documented honestly (correction,
  2026-10-03: an earlier version of this file claimed a heuristic had been
  added; the function still counts every pool transaction, because the
  Blockfrost address-transactions payload carries no swap marker — see
  README "Limitations")
- Missing error handling for network requests → wrapped requests with try/except and clear RuntimeError messages
- API key validation improved → HEADERS empty dict check now reliable
- Unused parameters removed → cleaned up signature
- CSV export failed if pandas missing → wrapped export in try/except
- No user feedback on mock mode → added warning print

## New features for LP fee tracking
- CLI interface with argparse
- Web dashboard `index.html` for quick estimates
- Mock data support for testing without Blockfrost key
- Export to CSV for historical analysis

## Fixed 2026-10-03 (each reproduced before fixing)
- README documented `--lp-address`, a flag that never existed — the
  documented command always died in argparse. README now shows the real
  `--pool / --lp-balance / --total-supply` interface (guarded by a test).
- Real mode reported `0.000000 ADA` for every pool: the per-transaction
  estimator returned a hard-coded zero while presenting the total as a
  result. Real mode now reports fee totals as *unavailable* (deriving
  them needs Minswap datum parsing) — never a fabricated zero.
- No position validation: a negative balance produced a −5% share and
  negative rewards; a balance 5× the supply produced a 500% share. CLI
  and web dashboard now reject negative / over-supply / zero-supply
  positions, and the dashboard accepts a legitimate 0 balance (its old
  falsy check rejected it as "fill all fields").
- Mock CSV rows had empty timestamps: the mock transactions' `block_time`
  was fetched, then discarded. Timestamps now flow into the records/CSV.
- Results were converted to `float`, defeating the Decimal precision
  above. Amounts stay `Decimal` end to end.
- CSV export depended on pandas; it now uses the stdlib `csv` module and
  pandas is out of `requirements.txt`. `requests`/`dotenv` became lazy /
  optional, so mock mode and the tests run on the standard library alone.
- `.github/FUNDING.yml` used a `cardano:` key GitHub doesn't support, so
  the file was silently ignored; replaced with a valid `custom:` link.
- Added `.gitignore` (`.env` holds a live API key and was one
  `git add .` away from being committed), first test suite, viewport/OG
  tags and @kshot9000 attribution on the dashboard.

## Fixed 2026-10-04 (each reproduced before fixing)
- `parse_decimal` failed open: any unparseable amount (`abc`, empty,
  `1,000`, `0x10`, `None`) silently became `Decimal("0")`, so the CLI
  exited 0 reporting a 0% share / 0 rewards as if calculated. It now
  raises `ValueError`, and the CLI exits 2 via `parser.error`.
- `NaN` amounts crashed instead of being rejected: `Decimal("NaN")`
  parses, and its comparisons raised `decimal.InvalidOperation` (not a
  `ValueError`), so the CLI died with a traceback. An infinite supply
  was also accepted and reported a ~0 share. Non-finite values are now
  rejected up front, matching the dashboard's `Number.isFinite` check.
- `BLOCKFROST_NETWORK` was interpolated unchecked into the Blockfrost
  host name; values containing path/query characters built a malformed
  or wrong-host URL. It is now validated against
  `mainnet` / `preprod` / `preview`.
