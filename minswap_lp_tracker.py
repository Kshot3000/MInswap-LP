"""
Minswap LP Fee Tracker
Estimates a liquidity provider's share of Minswap pool trading fees.

Honest scope (see README "Limitations"):
- Mock mode (no BLOCKFROST_API_KEY) uses two clearly-labelled demo
  transactions so the math and CSV export can be tried offline.
- Real mode lists the pool address's recent transactions from Blockfrost
  and computes the caller's LP share, but per-swap trading fees are
  reported as *unavailable*: deriving them requires parsing Minswap pool
  datums/redeemers, which this tool does not do yet. It never reports a
  fabricated 0.000000 ADA as if it were a measured total.
"""

import argparse
import csv
import os
import sys
from decimal import Decimal, InvalidOperation

try:  # .env loading is a convenience only; plain env vars work without it.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

MINSWAP_FEE = Decimal("0.003")  # 0.3% per swap, kept for the future datum parser

MOCK_TRANSACTIONS = [
    {"tx_hash": "mock_tx_1", "block_time": 1700000000},
    {"tx_hash": "mock_tx_2", "block_time": 1700003600},
]
# Deterministic demo fee per mock transaction (labelled mock everywhere).
MOCK_FEE_ADA = Decimal("0.0012")


def api_key():
    """Read the key at call time so tests/embedders can change the env."""
    return os.getenv("BLOCKFROST_API_KEY") or None


def mock_mode():
    return api_key() is None


def base_url():
    network = os.getenv("BLOCKFROST_NETWORK", "mainnet")
    return f"https://cardano-{network}.blockfrost.io/api/v0"


def _get_json(url):
    try:
        import requests
    except ImportError as e:
        raise RuntimeError(
            "The 'requests' package is required in real mode: "
            "pip install -r requirements.txt"
        ) from e
    try:
        resp = requests.get(
            url, headers={"project_id": api_key()}, timeout=30
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Blockfrost request failed for {url}: {e}") from e


def fetch_pool_transactions(pool_address, limit=100):
    """Fetch recent transactions for a Minswap pool address."""
    if mock_mode():
        return [dict(tx) for tx in MOCK_TRANSACTIONS[:limit]]
    txs = _get_json(f"{base_url()}/addresses/{pool_address}/transactions")
    return txs[:limit]


def is_swap_tx(tx):
    """Whether a pool-address transaction counts toward the fee scan.

    The Blockfrost address-transactions payload carries no marker that
    distinguishes swaps from liquidity deposits/withdrawals, so this
    currently counts every transaction touching the pool address. That
    over-counts non-swap activity; see README "Limitations".
    """
    return True


def estimate_fee(tx):
    """Fee record for one transaction.

    Mock mode returns the deterministic demo fee. Real mode returns
    ``estimated_fee_ada=None`` (unavailable): a swap's trading fee is
    0.3% of its volume, and the volume lives in the Minswap datum /
    redeemer data, not in the plain transaction payload. The Cardano
    network fee Blockfrost reports for a transaction is NOT the Minswap
    trading fee and is never substituted for it.
    """
    record = {"tx_hash": tx.get("tx_hash"), "timestamp": tx.get("block_time")}
    if mock_mode():
        record["estimated_fee_ada"] = MOCK_FEE_ADA
        record["fee_source"] = "mock"
    else:
        record["estimated_fee_ada"] = None
        record["fee_source"] = "unavailable"
    return record


def parse_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def validate_position(lp_balance, total_lp_supply):
    """Parse and sanity-check an LP position; raises ValueError."""
    balance = parse_decimal(lp_balance)
    supply = parse_decimal(total_lp_supply)
    if balance < 0:
        raise ValueError("LP balance cannot be negative")
    if supply < 0:
        raise ValueError("Total LP supply cannot be negative")
    if balance > supply:
        raise ValueError(
            "LP balance cannot exceed total LP supply "
            f"({balance} > {supply})"
        )
    return balance, supply


def calculate_lp_rewards(pool_address, lp_balance, total_lp_supply):
    """LP share plus the sum of the fees that are actually known.

    ``total_fees_ada`` / ``user_rewards_ada`` are Decimal, or None when
    no transaction had a derivable fee (real mode today) — never a
    fabricated zero presented as a measurement.
    """
    balance, supply = validate_position(lp_balance, total_lp_supply)
    share = (balance / supply) if supply > 0 else Decimal("0")

    txs = fetch_pool_transactions(pool_address)
    records = []
    known_fees = []
    for tx in txs:
        if not is_swap_tx(tx):
            continue
        fee_info = estimate_fee(tx)
        fee = fee_info["estimated_fee_ada"]
        if fee is not None:
            known_fees.append(fee)
        records.append(
            {
                "tx_hash": fee_info["tx_hash"],
                "timestamp": fee_info["timestamp"],
                "estimated_fee_ada": str(fee) if fee is not None else "",
                "fee_source": fee_info["fee_source"],
            }
        )

    total_fees = sum(known_fees, Decimal("0")) if known_fees else None
    return {
        "pool_address": pool_address,
        "total_fees_ada": total_fees,
        "lp_share": share,
        "user_rewards_ada": (total_fees * share) if total_fees is not None else None,
        "tx_count": len(records),
        "records": records,
        "mock_mode": mock_mode(),
    }


def export_csv(records, output_path):
    """Write records with the stdlib csv module (no pandas needed)."""
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["tx_hash", "timestamp", "estimated_fee_ada", "fee_source"]
        )
        writer.writeheader()
        for record in records:
            writer.writerow(record)
    return output_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Track Minswap LP fee rewards")
    parser.add_argument("--pool", required=True, help="Minswap pool address")
    parser.add_argument("--lp-balance", required=True, help="Your LP token balance")
    parser.add_argument("--total-supply", required=True, help="Total LP supply")
    parser.add_argument("--output", default="lp_rewards.csv", help="Output CSV file")
    args = parser.parse_args(argv)

    if mock_mode():
        print(
            "WARNING: Running in MOCK MODE - BLOCKFROST_API_KEY not set. "
            "Using demo data."
        )

    try:
        result = calculate_lp_rewards(
            pool_address=args.pool,
            lp_balance=args.lp_balance,
            total_lp_supply=args.total_supply,
        )
    except ValueError as e:
        parser.error(str(e))

    print(f"Pool: {result['pool_address']}")
    if result["total_fees_ada"] is None:
        print(
            "Total fees accrued: unavailable — per-swap trading fees "
            "require parsing Minswap pool datums, which this tool does "
            "not do yet (see README Limitations). No figure is reported "
            "rather than a fabricated zero."
        )
    else:
        print(f"Total fees accrued (estimated): {result['total_fees_ada']:.6f} ADA")
    print(f"Your LP share: {result['lp_share'] * 100:.4f}%")
    if result["user_rewards_ada"] is None:
        print("Your estimated rewards: unavailable (see above)")
    else:
        print(f"Your estimated rewards: {result['user_rewards_ada']:.6f} ADA")
    print(f"Transactions analyzed: {result['tx_count']}")

    try:
        export_csv(result["records"], args.output)
        print(f"Details exported to {args.output}")
    except OSError as e:
        print(f"Could not export CSV: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
