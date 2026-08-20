"""
OctoBus capability gateway client.

CRITICAL: This module ensures ALL capability calls go through the OctoBus gateway.
The agent NEVER directly calls backend services. This is the single entry point for:
  1. Port scanning (portscan service)
  2. Asset querying (assetquery service)

Design rationale (per assessment requirement Q10):
  - Credentials managed centrally in OctoBus capset, not scattered in agent env
  - Method-level whitelist enforced by capset (least privilege)
  - All calls logged as NDJSON audit trail by OctoBus
  - Backend service ports not exposed to agent network
  - Protocol unified via Connect RPC

Protocol: Connect RPC (HTTP/1.1 friendly, JSON mapping)
  - Chosen over raw gRPC for easier debugging and no HTTP/2 dependency
  - Chosen over MCP because this is a service call, not a tool ecosystem interaction

OctoBus Connect routing (verified against deployed gateway):
  POST {endpoint}/capsets/{capset}/connect/{instance}/{service.v1.Service/Method}
  Authorization: Bearer <capset token>
"""
import json
import time
import httpx
from typing import Optional


class OctoBusClient:
    """Client for calling OctoBus gateway via Connect RPC protocol."""

    def __init__(
        self,
        endpoint: str,
        token: str,
        capset: str = "exposure-scan",
        portscan_instance: str = "portscan-default",
        portscan_method: str = "portscan.v1.PortScanService/ScanPorts",
        assetquery_instance: str = "assetquery-default",
        assetquery_method: str = "assetquery.v1.AssetQueryService/QueryAssets",
        timeout: int = 30,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.token = token
        self.capset = capset
        self.portscan_instance = portscan_instance
        self.portscan_method = portscan_method
        self.assetquery_instance = assetquery_instance
        self.assetquery_method = assetquery_method
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Connect-Protocol-Version": "1",
        }

    def _call(self, instance: str, method: str, payload: dict) -> dict:
        """
        Execute a Connect RPC call through the OctoBus gateway.
        URL pattern: {endpoint}/capsets/{capset}/connect/{instance}/{method}
        where method is the full protobuf method path.
        """
        url = f"{self.endpoint}/capsets/{self.capset}/connect/{instance}/{method}"
        start_ts = time.time()
        call_id = f"{instance}_{method.split('/')[-1]}_{int(start_ts*1000)}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=self.headers)

            elapsed_ms = int((time.time() - start_ts) * 1000)

            if resp.status_code != 200:
                raise RuntimeError(
                    f"OctoBus call failed: {call_id} "
                    f"status={resp.status_code} body={resp.text[:500]}"
                )

            result = resp.json()

            # Log the call for audit trail (OctoBus also logs server-side,
            # but we keep a client-side record for correlation)
            print(
                json.dumps({
                    "type": "octobus_call",
                    "call_id": call_id,
                    "capset": self.capset,
                    "instance": instance,
                    "method": method,
                    "status_code": resp.status_code,
                    "elapsed_ms": elapsed_ms,
                    "timestamp": start_ts,
                }),
                flush=True,
            )
            return result

        except httpx.TimeoutException:
            raise RuntimeError(f"OctoBus call timed out: {call_id}")
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"OctoBus unreachable: {call_id}. "
                f"Check network config - OctoBus should be on same bridge network. "
                f"Error: {e}"
            )

    def scan_ports(self, host: str, ports: list, timeout_per_port: int = 5) -> dict:
        """
        Call portscan service to scan specified ports on a host.
        Returns: {"host": str, "results": [{"port": int, "state": str, "banner": str}]}
        """
        payload = {
            "host": host,
            "ports": ports,
            "timeout_per_port": timeout_per_port,
        }
        return self._call(
            instance=self.portscan_instance,
            method=self.portscan_method,
            payload=payload,
        )

    def query_assets(self, asset_filter: Optional[dict] = None) -> dict:
        """
        Call assetquery service to retrieve asset inventory.
        Returns: {"assets": [{"ip": str, "hostname": str, "tags": [str], "owner": str}]}
        """
        payload = {"filter": asset_filter or {}}
        return self._call(
            instance=self.assetquery_instance,
            method=self.assetquery_method,
            payload=payload,
        )
