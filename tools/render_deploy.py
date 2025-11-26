"""Small helper to trigger and monitor a Render deploy via API.

Usage:
  - Set environment variable `RENDER_API_KEY` or pass `--api-key`.
  - Provide `--service-id` (Render service id) or set `RENDER_SERVICE_ID`.

Example:
  python tools/render_deploy.py --service-id srv-xxxxxxxx --wait

This script will POST a deploy request and poll the deploy status until
it finishes or times out.
"""
import os
import time
import argparse
try:
    import requests
except Exception:
    requests = None


API_BASE = "https://api.render.com/v1"


def trigger_deploy(api_key, service_id):
    url = f"{API_BASE}/services/{service_id}/deploys"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={})
    resp.raise_for_status()
    return resp.json()


def get_deploy_status(api_key, service_id, deploy_id):
    url = f"{API_BASE}/services/{service_id}/deploys/{deploy_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def list_deploys(api_key, service_id, limit=5):
    url = f"{API_BASE}/services/{service_id}/deploys"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(url, headers=headers, params={"limit": limit})
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-id", help="Render service id (srv-xxx)")
    parser.add_argument("--api-key", help="Render API key (alternatively set RENDER_API_KEY env var)")
    parser.add_argument("--wait", action="store_true", help="Poll deploy status until finished")
    parser.add_argument("--timeout", type=int, default=900, help="Timeout in seconds when waiting (default 900)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("RENDER_API_KEY")
    service_id = args.service_id or os.environ.get("RENDER_SERVICE_ID")

    if requests is None:
        print("Package 'requests' is required. Install with: pip install requests")
        return 2

    if not api_key:
        print("Missing Render API key. Provide --api-key or set RENDER_API_KEY environment variable.")
        return 2
    if not service_id:
        print("Missing Render service id. Provide --service-id or set RENDER_SERVICE_ID environment variable.")
        return 2

    print(f"Triggering deploy for service {service_id}...")
    try:
        deploy = trigger_deploy(api_key, service_id)
    except Exception as e:
        print("Failed to trigger deploy:", e)
        return 1

    deploy_id = deploy.get("id")
    print(f"Deploy triggered: id={deploy_id}")
    print("You can view details in the Render dashboard or use this script with --wait to poll status.")

    if args.wait and deploy_id:
        started = time.time()
        print("Polling deploy status...")
        while True:
            try:
                info = get_deploy_status(api_key, service_id, deploy_id)
            except Exception as e:
                print("Error fetching deploy status:", e)
                return 1

            state = info.get("state")
            print(f"  state={state}  updatedAt={info.get('updatedAt')}")
            if state in ("success", "failed", "canceled"):
                print("Final state:", state)
                if state == "success":
                    return 0
                else:
                    return 1

            if time.time() - started > args.timeout:
                print("Timeout waiting for deploy to finish")
                return 1

            time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
