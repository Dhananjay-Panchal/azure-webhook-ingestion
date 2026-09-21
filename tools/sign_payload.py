from __future__ import annotations

import argparse
from pathlib import Path

from webhook_ingestion.security import sign


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an HMAC signature for a JSON payload")
    parser.add_argument("payload")
    parser.add_argument("--secret", required=True)
    args = parser.parse_args()
    print(sign(args.secret, Path(args.payload).read_bytes()))


if __name__ == "__main__":
    main()

