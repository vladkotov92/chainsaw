# CHAINSAW — on-chain intelligence tool

Interactive TUI app to fetch and export on-chain transactions for **Bitcoin** and **Ethereum** wallets — no API key required.

---

## Features

- Auto-detection of chain from address format (BTC / ETH)
- Live address validation via public APIs
- Custom date range filter
- Optional fetch limit (pages for BTC, transactions for ETH)
- Exports a clean **CSV** file with all transaction data
- Terminal display with summary and transaction timeline
- Zero configuration — works out of the box

## Supported chains

| Chain            | API                                          | Address format             |
| ---------------- | -------------------------------------------- | -------------------------- |
| ₿ Bitcoin (BTC)  | [Blockstream.info](https://blockstream.info) | `1...` / `3...` / `bc1...` |
| Ξ Ethereum (ETH) | [Blockscout.com](https://eth.blockscout.com) | `0x...` (42 hex chars)     |

## Requirements

- Python 3.10+
- [requests](https://pypi.org/project/requests/)

```bash
pip install requests
```

> If you have multiple Python versions, use:
>
> ```bash
> python3 -m pip install requests
> ```

## Usage

```bash
python3 btc_tracker.py
```

### Flow

```
STEP 1 — Enter wallet address      (chain detected automatically)
STEP 2 — Set date range            (mm/dd/yyyy)
STEP 3 — Set fetch limit           (optional: max pages / transactions)
STEP 4 — Review & confirm
```

## CSV output

Reports are saved in the current directory.
Filename format: `btc_report_<wallet>_<from>_<to>.csv` / `eth_report_<wallet>_<from>_<to>.csv`

### BTC columns

| Column         | Description                           |
| -------------- | ------------------------------------- |
| `n`            | Row index                             |
| `date_time`    | Timestamp (ISO 8601, UTC)             |
| `txid`         | Transaction ID                        |
| `block_height` | Block number                          |
| `type`         | `IN` / `OUT` / `IN(net)` / `OUT(net)` |
| `received_btc` | BTC received by the wallet in this tx |
| `sent_btc`     | BTC sent from the wallet in this tx   |
| `amount_btc`   | Net amount relevant to the wallet     |
| `fee_btc`      | Miner fee                             |
| `from`         | All input addresses (`;` separated)   |
| `to`           | All output addresses (`;` separated)  |

### ETH columns

| Column           | Description                     |
| ---------------- | ------------------------------- |
| `n`              | Row index                       |
| `date_time`      | Timestamp (ISO 8601, UTC)       |
| `txhash`         | Transaction hash                |
| `block`          | Block number                    |
| `type`           | `IN` / `OUT`                    |
| `amount_eth`     | Value transferred (ETH)         |
| `from`           | Sender address                  |
| `to`             | Recipient address               |
| `fee_eth`        | Gas fee paid (ETH)              |
| `gas_used`       | Gas units consumed              |
| `gas_price_gwei` | Gas price (Gwei)                |
| `status`         | `ok` / `error`                  |
| `method`         | Contract method called (if any) |

## Privacy

All API calls are **read-only**. No data is stored or sent anywhere beyond the public blockchain APIs listed above.

## License

MIT — see [LICENSE](LICENSE)
