# Bugs Fixed

## Original issues addressed
- Invalid identifier `MIN SWAP_FEE` → renamed to `MINSWAP_FEE`
- Used float for financial calculations → switched to `Decimal` for precision
- No mock mode for local development → added `MOCK_MODE` when API key missing
- `is_swap_tx` always returned True → added placeholder heuristic and comments for real implementation
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
