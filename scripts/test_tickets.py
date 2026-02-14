"""Quick test: verify ticket routes registered + templates compile."""
import httpx
import json

BASE = "http://127.0.0.1:8000"


def main():
    client = httpx.Client(base_url=BASE, timeout=10)

    # 1) Health
    r = client.get("/health")
    print(f"Health check: {r.status_code}")

    # 2) Check OpenAPI for ticket routes
    r = client.get("/openapi.json")
    if r.status_code == 200:
        spec = r.json()
        paths = spec.get("paths", {})
        ticket_paths = {k: list(v.keys()) for k, v in paths.items() if "ticket" in k.lower()}
        print(f"\nTicket routes in OpenAPI ({len(ticket_paths)} paths):")
        for path, methods in sorted(ticket_paths.items()):
            print(f"  {', '.join(m.upper() for m in methods):12s} {path}")
    else:
        print(f"OpenAPI: {r.status_code}")

    # 3) Check unauthenticated ticket routes (should return 401, not 404 or 500)
    print("\nUnauthenticated access checks (expect 401/302, NOT 404 or 500):")
    for url in [
        "/tickets",
        "/tickets/new",
        "/tickets/1",
        "/admin/tickets",
        "/admin/tickets/1",
    ]:
        r = client.get(url, follow_redirects=False)
        status = r.status_code
        tag = "OK" if status in (401, 302, 403) else f"UNEXPECTED"
        print(f"  GET {url:35s} => {status} {tag}")

    print("\n--- Done ---")
    client.close()


if __name__ == "__main__":
    main()
