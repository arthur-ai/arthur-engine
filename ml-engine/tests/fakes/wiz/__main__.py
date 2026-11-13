"""Serve the fake Wiz tenant: `uv run python -m tests.fakes.wiz --port 8099`."""

import argparse
import logging
import os

from .server import DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET, FAULTS, FakeWiz


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m tests.fakes.wiz",
        description="A fake Wiz token endpoint and GraphQL API with synthetic data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="faults (--fault, FAKE_WIZ_FAULT, or POST /_control/fault?mode=...):\n"
        + "\n".join(f"  {name:18} {what}" for name, what in FAULTS.items()),
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="most nodes per page, whatever `first` asks; small values exercise paging",
    )
    parser.add_argument(
        "--fault",
        choices=sorted(FAULTS),
        default=os.getenv("FAKE_WIZ_FAULT", "none") or "none",
    )
    parser.add_argument("--client-id", default=DEFAULT_CLIENT_ID)
    parser.add_argument(
        "--client-secret",
        default=os.getenv("FAKE_WIZ_CLIENT_SECRET") or DEFAULT_CLIENT_SECRET,
    )
    parser.add_argument("--token-lifetime", type=int, default=3600)
    parser.add_argument(
        "--retry-after",
        default="1",
        help="seconds, for rate-limit-once",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    fake = FakeWiz(
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        client_secret=args.client_secret,
        page_size=args.page_size,
        fault=args.fault,
        token_lifetime=args.token_lifetime,
        retry_after=args.retry_after,
    )
    print(
        f"Fake Wiz on {fake.base_url} (fault: {fake.fault}, page size {fake.page_size})\n"
        f"  token:   POST {fake.base_url}/oauth/token\n"
        f"  graphql: POST {fake.base_url}/graphql\n"
        f"  engine:  ARTHUR_ENGINE_WIZ_API_BASE_URL_OVERRIDE={fake.base_url}\n"
        f"  client_id={args.client_id}  client_secret=<--client-secret>",
        flush=True,
    )
    try:
        fake.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
