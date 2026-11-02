"""Bounded manual load test. No external requests occur until main() is called."""

import argparse
import json
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument(
        "--rate", type=float, default=2, help="Total maximum requests/second"
    )
    parser.add_argument(
        "--create-count", type=int, default=1, help="Bounded setup records"
    )
    parser.add_argument("--code", help="Reuse an existing code; creates no records")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    parsed = urlsplit(args.base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        parser.error("Use an HTTP(S) origin without credentials, path or query")
    if not (
        1 <= args.concurrency <= 20
        and 1 <= args.duration <= 300
        and 0 < args.rate <= 20
        and 1 <= args.create_count <= 10
    ):
        parser.error(
            "Bounds: concurrency 1-20, duration 1-300s, rate (0,20], records 1-10"
        )
    args.base_url = args.base_url.rstrip("/")
    return args


def request(opener, url, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with opener.open(req, timeout=3) as response:
            return response.status, response.read(65536)
    except HTTPError as exc:
        # 302 is an expected result; never follow redirects to third-party URLs.
        return exc.code, b""
    except (URLError, TimeoutError, OSError):
        return 0, b""


def main(argv=None):
    args = parse_args(argv)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "concurrency": args.concurrency,
                    "seconds": args.duration,
                    "max_rps": args.rate,
                    "new_records": 0 if args.code else args.create_count,
                }
            )
        )
        return
    opener = build_opener(NoRedirect())
    codes = [args.code] if args.code else []
    for _ in range(0 if args.code else args.create_count):
        status, body = request(
            opener,
            args.base_url + "/api/urls",
            "POST",
            {"url": "https://example.com/kata-load"},
        )
        if status != 201:
            raise SystemExit(f"Setup failed with HTTP {status}; stopping without load")
        codes.append(json.loads(body)["code"])
        time.sleep(1 / args.rate)
    lock = threading.Lock()
    started = time.monotonic()
    deadline = started + args.duration
    schedule = started
    sequence = 0
    results = []

    def worker():
        nonlocal schedule, sequence
        local_opener = build_opener(NoRedirect())
        while True:
            with lock:
                slot = max(schedule, time.monotonic())
                if slot >= deadline:
                    return
                schedule = slot + 1 / args.rate
                index = sequence
                sequence += 1
            time.sleep(max(0, slot - time.monotonic()))
            if time.monotonic() >= deadline:
                return
            code = quote(codes[index % len(codes)], safe="")
            stats = index % 5 == 4
            path = f"/api/urls/{code}/stats" if stats else f"/r/{code}"
            before = time.monotonic()
            status, _ = request(local_opener, args.base_url + path)
            with lock:
                results.append(
                    (time.monotonic() - before, status == (200 if stats else 302))
                )

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(lambda _: worker(), range(args.concurrency)))
    latencies = sorted(duration * 1000 for duration, _ in results)
    errors = sum(not ok for _, ok in results)
    print(
        json.dumps(
            {
                "requests": len(results),
                "errors": errors,
                "error_rate": errors / len(results) if results else 0,
                "p50_ms": statistics.median(latencies) if latencies else None,
                "p95_ms": latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
                if latencies
                else None,
                "new_records": 0 if args.code else args.create_count,
            }
        )
    )
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
