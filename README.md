# Minswap LP Fee Tracker

Track your Minswap liquidity provider (LP) position on Cardano: your share
of a pool, the pool address's recent transactions (via Blockfrost), and —
in demo mode — how fee rewards would be attributed to your share.

## Features
- Fetch recent transactions for any Minswap pool address from Blockfrost
- Compute your LP share (`your balance / total LP supply`) with `Decimal`
  precision and input validation (negative or over-supply positions are
  rejected instead of producing negative or >100% shares)
- Export a CSV of the scanned transactions with the stdlib `csv` module
- Mock mode with clearly labelled demo data when no API key is set, so the
  math and export can be tried offline with zero installs
- A static demo calculator in `index.html` using the same validation rules

## Setup
1. (Real mode only) Set `BLOCKFROST_API_KEY` in `.env` — see `.env.example`.
   Without a key the tool runs in mock mode and says so. `.env` is
   git-ignored; never commit a real key.
2. Real mode only: `pip install -r requirements.txt`
   (mock mode and the test suite run on the Python standard library alone)
3. Run:
   `python minswap_lp_tracker.py --pool <pool_address> --lp-balance <your_lp_balance> --total-supply <total_lp_supply>`

## Limitations — read before trusting any number
- **Real mode does not report a fee total yet.** A swap's trading fee is
  0.3% of its volume, and the volume lives in the Minswap pool datum /
  redeemer data, which this tool does not parse yet. Rather than print a
  fabricated `0.000000 ADA`, real mode reports the fee total and your
  rewards as **unavailable**, alongside your LP share and the transaction
  count. (The Cardano network fee on a transaction is not the Minswap
  trading fee and is never substituted for it.)
- **Every pool transaction is counted.** The Blockfrost
  address-transactions payload has no marker distinguishing swaps from
  liquidity deposits/withdrawals, so the scan counts all of them.
- **Mock mode is demo data.** Two fixed demo transactions at a fixed demo
  fee (0.0012 ADA each). The web dashboard likewise uses a fixed mock fee
  total and labels it as demo data.

## Tests
`python -m unittest discover -s tests -v` — standard library only.
Covers the share math, position validation, mock timestamps in the CSV,
real-mode "unavailable, never zero" behaviour (Blockfrost stubbed),
stdlib CSV export, the README/CLI flag match, and the dashboard's
validation logic (via Node, when available).

## Donate
Cardano donation address:
`addr1q8hnl6vl5a6k3rw3n5g3jtte696zcl76kfatzv7gpswa9r0dj7fma6klq55y4ffm7tf0em09udnyhuk4ah92pl5x9jpqjae44v`

Built by [@kshot9000](https://x.com/kshot9000) · [github.com/Kshot3000](https://github.com/Kshot3000)

## License
MIT
