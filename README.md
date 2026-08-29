# Minswap LP Fee Tracker

Track your Minswap liquidity provider trading fee rewards on Cardano.

## Features
- Fetch pool swap history for any Minswap pool
- Calculate cumulative trading fees earned
- Estimate rewards per LP token held
- Export CSV of fee accruals over time
- Simple CLI interface

## Setup
1. Set BLOCKFROST_API_KEY in `.env`
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python minswap_lp_tracker.py --pool <pool_address> --lp-address <your_lp_address>`

## Notes
Minswap pools charge 0.3% per swap, split to LPs. This tool queries on-chain swap transactions and attributes fees proportionally.

## License
MIT
