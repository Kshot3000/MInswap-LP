"""Tests for the Minswap LP fee tracker.

Standard library only:  python -m unittest discover -s tests -v
The tracker's network/optional dependencies are lazy, so mock mode, the
math, validation and CSV export are all exercised with zero installs.
Real mode is tested with a stubbed `requests` module in sys.modules.
"""

import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import minswap_lp_tracker as tracker

REPO = Path(__file__).resolve().parents[1]
DONATION = (
    "addr1q8hnl6vl5a6k3rw3n5g3jtte696zcl76kfatzv7gpswa9r0dj7fma"
    "6klq55y4ffm7tf0em09udnyhuk4ah92pl5x9jpqjae44v"
)


def no_key_env():
    return mock.patch.dict(os.environ, {}, clear=True)


class MockModeTests(unittest.TestCase):
    def test_share_and_rewards_math_is_exact_decimal(self):
        with no_key_env():
            result = tracker.calculate_lp_rewards("addr1pool", "250", "1000")
        self.assertIsInstance(result["total_fees_ada"], Decimal)
        self.assertEqual(result["total_fees_ada"], Decimal("0.0024"))
        self.assertEqual(result["lp_share"], Decimal("0.25"))
        self.assertEqual(result["user_rewards_ada"], Decimal("0.0006"))
        self.assertEqual(result["tx_count"], 2)
        self.assertTrue(result["mock_mode"])

    def test_mock_timestamps_reach_the_records(self):
        # Regression: mock block_time used to be fetched then discarded,
        # leaving the CSV timestamp column empty.
        with no_key_env():
            result = tracker.calculate_lp_rewards("addr1pool", "1", "4")
        self.assertEqual(
            [r["timestamp"] for r in result["records"]], [1700000000, 1700003600]
        )
        self.assertTrue(
            all(r["fee_source"] == "mock" for r in result["records"])
        )


class ValidationTests(unittest.TestCase):
    def test_negative_balance_rejected(self):
        with no_key_env(), self.assertRaises(ValueError):
            tracker.calculate_lp_rewards("addr1pool", "-50", "1000")

    def test_negative_supply_rejected(self):
        with no_key_env(), self.assertRaises(ValueError):
            tracker.calculate_lp_rewards("addr1pool", "10", "-1000")

    def test_balance_above_supply_rejected(self):
        # Used to print a 500% share and 5x-inflated rewards.
        with no_key_env(), self.assertRaises(ValueError):
            tracker.calculate_lp_rewards("addr1pool", "5000", "1000")

    def test_zero_position_is_valid(self):
        with no_key_env():
            result = tracker.calculate_lp_rewards("addr1pool", "0", "0")
        self.assertEqual(result["lp_share"], Decimal("0"))
        self.assertEqual(result["user_rewards_ada"], Decimal("0"))


class RealModeHonestyTests(unittest.TestCase):
    """With an API key + stubbed Blockfrost, fees must be reported as
    unavailable — never the old fabricated 0.000000 ADA total."""

    def _stub_requests(self):
        pool_txs = [
            {"tx_hash": "aa" * 32, "block_time": 1700000000},
            {"tx_hash": "bb" * 32, "block_time": 1700003600},
        ]

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return pool_txs

        fake = types.ModuleType("requests")
        fake.RequestException = RuntimeError
        fake.get = lambda url, headers=None, timeout=None: Resp()
        return fake

    def test_real_mode_reports_unavailable_not_zero(self):
        env = {"BLOCKFROST_API_KEY": "test_key_not_real"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.dict(
            sys.modules, {"requests": self._stub_requests()}
        ):
            result = tracker.calculate_lp_rewards("addr1pool", "250", "1000")
        self.assertFalse(result["mock_mode"])
        self.assertIsNone(result["total_fees_ada"])
        self.assertIsNone(result["user_rewards_ada"])
        self.assertEqual(result["lp_share"], Decimal("0.25"))
        self.assertEqual(result["tx_count"], 2)
        self.assertTrue(
            all(r["fee_source"] == "unavailable" for r in result["records"])
        )
        self.assertTrue(all(r["estimated_fee_ada"] == "" for r in result["records"]))


class CsvTests(unittest.TestCase):
    def test_stdlib_csv_export_round_trip(self):
        with no_key_env():
            result = tracker.calculate_lp_rewards("addr1pool", "250", "1000")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            tracker.export_csv(result["records"], path)
            rows = list(csv.DictReader(path.open()))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["tx_hash"], "mock_tx_1")
        self.assertEqual(rows[0]["timestamp"], "1700000000")
        self.assertEqual(rows[0]["estimated_fee_ada"], "0.0012")

    def test_no_pandas_anywhere(self):
        source = (REPO / "minswap_lp_tracker.py").read_text()
        requirements = (REPO / "requirements.txt").read_text()
        self.assertNotIn("import pandas", source)
        self.assertNotIn("pandas", requirements)


class DocsAndConfigTests(unittest.TestCase):
    def test_readme_documents_the_real_cli(self):
        readme = (REPO / "README.md").read_text()
        # The old README documented --lp-address, which never existed.
        self.assertNotIn("--lp-address", readme)
        for flag in ("--pool", "--lp-balance", "--total-supply"):
            self.assertIn(flag, readme)

    def test_documented_flags_parse(self):
        argv = [
            "--pool", "addr1pool", "--lp-balance", "250",
            "--total-supply", "1000", "--output", "x.csv",
        ]
        with no_key_env(), tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            argv[-1] = str(Path(tmp) / "x.csv")
            with redirect_stdout(out):
                code = tracker.main(argv)
        self.assertEqual(code, 0)
        self.assertIn("25.0000%", out.getvalue())

    def test_funding_yml_uses_a_supported_key(self):
        funding = (REPO / ".github" / "FUNDING.yml").read_text()
        self.assertNotRegex(funding, r"(?m)^cardano:")
        self.assertIn("custom:", funding)
        self.assertIn(DONATION, funding)

    def test_gitignore_protects_the_api_key(self):
        gitignore = (REPO / ".gitignore").read_text()
        self.assertIn(".env", gitignore)

    def test_donation_address_is_kyles_verified_one(self):
        for name in ("README.md", "DONATION.md", "index.html"):
            self.assertIn(DONATION, (REPO / name).read_text(), name)


@unittest.skipUnless(shutil.which("node"), "node not available")
class DashboardTests(unittest.TestCase):
    def _compute(self, bal, sup):
        html = (REPO / "index.html").read_text()
        start = html.index("function validateAndCompute")
        end = html.index("function calculate")
        fn = html[start:end]
        script = fn + f"\nconsole.log(JSON.stringify(validateAndCompute({json.dumps(bal)}, {json.dumps(sup)})))"
        out = subprocess.run(
            ["node", "-e", script], capture_output=True, text=True, check=True
        )
        return json.loads(out.stdout.strip())

    def test_zero_balance_is_accepted(self):
        # The old falsy check rejected a legitimate 0 as "fill all fields".
        result = self._compute("0", "1000")
        self.assertNotIn("error", result)
        self.assertEqual(result["share"], 0)

    def test_negative_and_over_supply_rejected(self):
        self.assertIn("error", self._compute("-50", "1000"))
        self.assertIn("error", self._compute("5000", "1000"))
        self.assertIn("error", self._compute("10", "0"))
        self.assertIn("error", self._compute("", "1000"))

    def test_quarter_share(self):
        result = self._compute("250", "1000")
        self.assertAlmostEqual(result["share"], 0.25)
        self.assertAlmostEqual(result["rewards"], 0.0006)

    def test_dashboard_hygiene(self):
        html = (REPO / "index.html").read_text()
        self.assertIn('name="viewport"', html)
        self.assertIn("@kshot9000", html)
        self.assertIn("demo data", html.lower())


if __name__ == "__main__":
    unittest.main()
