"""Verify one complete session against the SDK and the real node resource socket."""
import argparse
import json
import os
import subprocess
import time

from agentcube import CodeInterpreterClient
from agentcube.exceptions import SessionNotFoundError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ssh", help="SSH config alias for the node (default: local)")
    parser.add_argument("--node-ctl", default="/opt/kuasar/bin/node-ctl")
    parser.add_argument("--socket", default="/run/node-ctl/node-ctl.sock")
    args = parser.parse_args()

    def reservations():
        command = ["sudo", "-n", args.node_ctl, "resource", "list", "--socket", args.socket]
        if args.ssh:
            import shlex
            command = ["ssh", args.ssh, shlex.join(command)]
        return json.loads(subprocess.check_output(command, text=True, timeout=15)) or []

    options = dict(name="kuasar-picod", namespace="kuasar-lab",
                   workload_manager_url=os.environ["WORKLOAD_MANAGER_URL"],
                   router_url=os.environ["ROUTER_URL"])
    baseline = reservations()
    if baseline:
        raise RuntimeError("verification requires an idle, dedicated node")

    client = CodeInterpreterClient(**options)
    sid = client.session_id
    try:
        active = reservations()
        if len(active) != 1 or active[0]["sandbox_id"] != sid or not active[0]["connected"]:
            raise RuntimeError(f"node allocation does not match SDK session {sid}")
        result = client.dp_client.execute_command_result(["/bin/sh", "-c", "echo hello"])
        if result["exit_code"] != 0 or result["stdout"] != "hello\n":
            raise RuntimeError(f"unexpected guest result: {result}")
    finally:
        client.stop()

    deadline = time.monotonic() + 20
    while reservations():
        if time.monotonic() > deadline:
            raise RuntimeError("node still holds a reservation after SDK deletion")
        time.sleep(0.5)
    stale = CodeInterpreterClient(session_id=sid, **options)
    try:
        stale.dp_client.execute_command_result(["/bin/echo", "unexpected"])
    except SessionNotFoundError:
        pass
    else:
        raise RuntimeError("Router still accepted the deleted session")
    finally:
        stale.dp_client.close()
        stale.cp_client.close()
    print(json.dumps({"session_id": sid, "baseline": baseline, "active": active,
                      "execution": result, "released": True, "stale_session_rejected": True}))


if __name__ == "__main__":
    main()
