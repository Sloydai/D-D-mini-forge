#!/usr/bin/env python3
"""
sloyd_api.py: zero-dependency Sloyd client for when the Sloyd MCP tools aren't connected,
and a small plan runner that respects the 5-concurrent-jobs limit.

Credentials come from SLOYD_CLIENT_ID / SLOYD_CLIENT_SECRET and are never printed.

  python sloyd_api.py balance
  python sloyd_api.py call generate_image '{"prompt": "...", "aspectRatio": "1:1"}' --wait --download out/
  python sloyd_api.py wait <jobId> [<jobId> ...] --download out/
  python sloyd_api.py plan plan.json --out out/          # dependency-ordered batch, max 5 at a time

Transport: by default tools are called on the hosted MCP endpoint over plain HTTP JSON-RPC
(https://api.sloyd.ai/api/mcp), which returns output URLs from get_job. --rest calls the
documented REST endpoints instead (https://api.sloyd.ai/api/jobs/...).

Plan file: a list of steps. A step runs once every step it references is done.
  [{"id": "concept", "tool": "generate_image", "args": {"prompt": "..."}},
   {"id": "side", "tool": "edit_image", "args": {"jobId": "{{concept.jobId}}", "prompt": "..."}},
   {"id": "mini", "tool": "generate_3d_from_images",
    "args": {"frontImage": {"url": "{{concept.imageUrl}}"}, "leftImage": {"url": "{{side.imageUrl}}"}}}]
Exit codes: 0 ok, 2 out of credits (402), 3 job failed, 4 auth/config error.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://api.sloyd.ai/api"
MCP = f"{BASE}/mcp"
GLB_URL = "https://storage.googleapis.com/ai-services-quality/jobs/{}.glb"
MAX_ACTIVE = 5

# Credit costs from https://www.sloyd.ai/api/pricing (also echoed in 402 "required").
COSTS = {
    "generate_image": 10, "edit_image": 15, "generate_skybox": 25, "generate_skybox_from_image": 25,
    "edit_skybox": 25, "generate_3d_from_text": 25, "generate_3d_from_image": 20,
    "generate_3d_from_images": 30, "retexture_model": 15, "split_model_into_parts": 40,
    "upload_image": 0, "get_job": 0, "get_credit_balance": 0, "get_generation_styles": 0,
}

REST = {  # tool -> (method, path, body kind)
    "generate_3d_from_text": ("POST", "/jobs/text-to-3d", "json"),
    "generate_3d_from_image": ("POST", "/jobs/image-to-3d", "multipart"),
    "generate_3d_from_images": ("POST", "/jobs/multi-image-to-3d", "multipart"),
    "upload_image": ("POST", "/jobs/image-upload", "multipart"),
    "generate_image": ("POST", "/jobs/text-to-image", "json"),
    "edit_image": ("POST", "/jobs/image-edit", "json"),
    "generate_skybox": ("POST", "/jobs/text-to-worldbox", "json"),
    "generate_skybox_from_image": ("POST", "/jobs/skybox-from-image", "json"),
    "edit_skybox": ("POST", "/jobs/skybox-edit", "json"),
    "retexture_model": ("POST", "/jobs/retexture", "json"),
    "split_model_into_parts": ("POST", "/jobs/split-to-parts", "json"),
    "get_credit_balance": ("GET", "/user/api-access/balance", None),
}


class SloydError(Exception):
    def __init__(self, status: int, message: str, body: dict | None = None):
        super().__init__(f"Sloyd API error {status}: {message}")
        self.status, self.body = status, body or {}


def creds() -> dict:
    cid, sec = os.environ.get("SLOYD_CLIENT_ID"), os.environ.get("SLOYD_CLIENT_SECRET")
    if not cid or not sec:
        print("Set SLOYD_CLIENT_ID and SLOYD_CLIENT_SECRET (API Dashboard -> API Keys).", file=sys.stderr)
        sys.exit(4)
    return {"x-client-id": cid, "x-client-secret": sec}


def http(method: str, url: str, headers: dict, data: bytes | None = None, timeout: int = 90):
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


# ----------------------------------------------------------------------------- MCP transport

def mcp_call(tool: str, args: dict) -> dict:
    payload = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "tools/call",
               "params": {"name": tool, "arguments": args}}
    h = {**creds(), "Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    status, raw = http("POST", MCP, h, json.dumps(payload).encode(), timeout=120)
    text = raw.decode("utf-8", "replace")
    msg = None
    for line in text.splitlines():  # streamable HTTP may answer as SSE
        if line.startswith("data: "):
            msg = json.loads(line[6:])
    if msg is None:
        try:
            msg = json.loads(text)
        except json.JSONDecodeError:
            raise SloydError(status, text[:300])
    if "error" in msg:
        raise SloydError(status, msg["error"].get("message", str(msg["error"])))
    res = msg["result"]
    sc = res.get("structuredContent")
    if sc is None:
        try:
            sc = json.loads(res["content"][0]["text"])
        except Exception:
            sc = {"text": res.get("content", [{}])[0].get("text", "")}
    if res.get("isError"):
        code = sc.get("statusCode") or (402 if "required" in sc else 500)
        raise SloydError(int(code), sc.get("message", str(sc)), sc)
    return sc


# ----------------------------------------------------------------------------- REST transport

def _fetch_image(spec: dict) -> tuple[bytes, str]:
    if "url" in spec:
        st, b = http("GET", spec["url"], {"User-Agent": "dnd-mini-forge"})
        if st != 200:
            raise SloydError(st, f"could not fetch {spec['url']}")
        return b, "image/png"
    import base64
    return base64.b64decode(spec["base64"]), spec.get("mimeType", "image/png")


def _multipart(fields: dict) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f"--{boundary}\r\n".encode()
        if isinstance(v, dict):
            data, mime = _fetch_image(v)
            out += f'Content-Disposition: form-data; name="{k}"; filename="{k}.png"\r\nContent-Type: {mime}\r\n\r\n'.encode()
            out += data + b"\r\n"
        else:
            out += f'Content-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def _urls(obj, found: dict) -> dict:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and v.startswith("http") and re.search(r"\.(png|jpe?g|webp|glb|exr|hdr)(\?|$)", v):
                found.setdefault(k, v)
            else:
                _urls(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _urls(v, found)
    return found


def rest_call(tool: str, args: dict) -> dict:
    h = creds()
    if tool == "get_job":
        st, raw = http("GET", f"{BASE}/jobs/{args['jobId']}", h)
        body = json.loads(raw or b"{}")
        if st >= 400:
            raise SloydError(st, body.get("message", str(body)), body)
        status = body.get("status")
        done = status in ("success", "error", "completed", "failed")
        ok = status in ("success", "completed")
        outputs = _urls(body, {}) if ok else {}
        if ok and not outputs:
            outputs = {"glbUrl": GLB_URL.format(body["id"])}
        return {"jobId": body.get("id"), "status": status, "done": done, "outputs": outputs,
                "errorMessage": body.get("errorMessage")}
    method, path, kind = REST[tool]
    data, ctype = None, None
    if kind == "json":
        data, ctype = json.dumps(args).encode(), "application/json"
    elif kind == "multipart":
        data, ctype = _multipart(args)
    if ctype:
        h["Content-Type"] = ctype
    st, raw = http(method, BASE + path, h, data, timeout=300)
    body = json.loads(raw or b"{}")
    if st >= 400:
        raise SloydError(st, body.get("message", str(body)), body)
    return body


def call(tool: str, args: dict, rest: bool = False) -> dict:
    if rest and tool == "get_job":
        time.sleep(min(int(args.get("wait", 0)), 30) / 3)
    return rest_call(tool, args) if rest else mcp_call(tool, args)


# ----------------------------------------------------------------------------- helpers

def wait_job(job_id: str, rest: bool = False, quiet: bool = False) -> dict:
    t0 = time.time()
    while True:
        r = call("get_job", {"jobId": job_id, "wait": 30}, rest)
        if r.get("done") or r.get("status") in ("success", "error"):
            r.setdefault("jobId", job_id)
            return r
        if not quiet:
            print(f"  {job_id}: {r.get('status', '?')} ({int(time.time() - t0)}s)", file=sys.stderr)
        if rest:
            time.sleep(10)


def download(outputs: dict, dest: Path, stem: str) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    files = []
    for key, url in outputs.items():
        urls = url if isinstance(url, list) else [url]
        for i, u in enumerate(urls):
            if not isinstance(u, str) or not u.startswith("http"):
                continue
            ext = re.search(r"\.(png|jpe?g|webp|glb|exr|hdr)(\?|$)", u)
            ext = ext.group(1) if ext else "bin"
            suffix = "" if len(urls) == 1 else f"_{i}"
            name = f"{stem}.{ext}" if key in ("glbUrl", "imageUrl") else f"{stem}_{key}{suffix}.{ext}"
            st, b = http("GET", u, {"User-Agent": "dnd-mini-forge"}, timeout=300)
            if st == 200:
                (dest / name).write_bytes(b)
                files.append(str(dest / name))
    return files


def balance(rest: bool = False) -> int:
    return int(call("get_credit_balance", {}, rest).get("balance", 0))


# ----------------------------------------------------------------------------- plan runner

REF = re.compile(r"\{\{\s*([\w-]+)\.([\w.]+)\s*\}\}")


def _resolve(obj, results: dict):
    if isinstance(obj, str):
        def sub(m):
            step, field = m.group(1), m.group(2)
            r = results[step]
            val = r.get(field) if field == "jobId" else r.get("outputs", {}).get(field)
            if val is None:
                raise KeyError(f"{step}.{field} not available (outputs: {list(r.get('outputs', {}))})")
            return val
        return REF.sub(sub, obj)
    if isinstance(obj, dict):
        return {k: _resolve(v, results) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve(v, results) for v in obj]
    return obj


def _deps(step: dict) -> set:
    return {m.group(1) for m in REF.finditer(json.dumps(step.get("args", {})))}


def run_plan(steps: list[dict], out: Path, rest: bool = False, yes: bool = False) -> int:
    cost = sum(COSTS.get(s["tool"], 0) for s in steps)
    bal = balance(rest)
    print(f"plan: {len(steps)} jobs, {cost} credits (~${cost / 75:.2f}); balance {bal}", file=sys.stderr)
    if cost > bal:
        print(f"Not enough credits: need {cost}, have {bal}. Top up at https://api-dashboard.sloyd.ai", file=sys.stderr)
        return 2
    if not yes and sys.stdin.isatty():
        if input("run it? [y/N] ").strip().lower() != "y":
            return 1
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    results: dict = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    pending = [s for s in steps if s["id"] not in results or results[s["id"]].get("status") != "success"]
    active: dict = {}  # id -> jobId
    failed = False
    while pending or active:
        # start what is ready
        for s in list(pending):
            if len(active) >= MAX_ACTIVE:
                break
            if not _deps(s) <= {k for k, v in results.items() if v.get("status") == "success"}:
                continue
            try:
                r = call(s["tool"], _resolve(s.get("args", {}), results), rest)
            except SloydError as e:
                if e.status == 429:
                    break  # wait for a running job to finish
                if e.status == 402:
                    print(f"402 out of credits at step {s['id']}: {e.body}", file=sys.stderr)
                    return 2
                raise
            active[s["id"]] = r["jobId"]
            pending.remove(s)
            print(f"started {s['id']} ({s['tool']}) -> {r['jobId']}", file=sys.stderr)
        if not active:
            if pending:
                stuck = [s["id"] for s in pending]
                if failed:
                    print(f"skipped (dependency failed): {stuck}", file=sys.stderr)
                    return 3
                time.sleep(30)  # 429 with nothing of ours active: someone else holds the slots
            continue
        # poll one round
        for sid, jid in list(active.items()):
            r = call("get_job", {"jobId": jid, "wait": 30 if len(active) == 1 else 5}, rest)
            if not (r.get("done") or r.get("status") in ("success", "error")):
                continue
            del active[sid]
            ok = r.get("status") in ("success", "completed")
            entry = {"jobId": jid, "status": "success" if ok else "error", "outputs": r.get("outputs", {})}
            if ok:
                entry["files"] = download(entry["outputs"], out, sid)
                print(f"done {sid}: {entry['files']}", file=sys.stderr)
            else:
                failed = True
                entry["error"] = r.get("errorMessage")
                print(f"FAILED {sid}: {entry['error']} (credits are refunded on failure)", file=sys.stderr)
            results[sid] = entry
            manifest_path.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    return 3 if failed else 0


# ----------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rest", action="store_true", help="use the REST endpoints instead of MCP-over-HTTP")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("balance")
    c = sub.add_parser("call"); c.add_argument("tool"); c.add_argument("args", nargs="?", default="{}")
    c.add_argument("--wait", action="store_true"); c.add_argument("--download"); c.add_argument("--name", default=None)
    w = sub.add_parser("wait"); w.add_argument("job_ids", nargs="+"); w.add_argument("--download")
    pl = sub.add_parser("plan"); pl.add_argument("file"); pl.add_argument("--out", required=True)
    pl.add_argument("--yes", action="store_true")
    a = p.parse_args(argv)
    try:
        if a.cmd == "balance":
            b = balance(a.rest)
            print(json.dumps({"balance": b, "usd_equivalent": round(b / 75, 2)}))
        elif a.cmd == "call":
            args = json.loads(a.args)
            r = call(a.tool, args, a.rest)
            if a.wait and "jobId" in r and a.tool not in ("get_job",):
                r = wait_job(r["jobId"], a.rest)
                if a.download and r.get("status") == "success":
                    r["files"] = download(r.get("outputs", {}), Path(a.download), a.name or r["jobId"])
            print(json.dumps(r, indent=2))
            return 3 if r.get("status") == "error" else 0
        elif a.cmd == "wait":
            res = []
            for j in a.job_ids:
                r = wait_job(j, a.rest)
                if a.download and r.get("status") == "success":
                    r["files"] = download(r.get("outputs", {}), Path(a.download), j)
                res.append(r)
            print(json.dumps(res, indent=2))
        elif a.cmd == "plan":
            return run_plan(json.loads(Path(a.file).read_text()), Path(a.out), a.rest, a.yes)
    except SloydError as e:
        print(str(e), file=sys.stderr)
        if e.status == 402:
            print(f"Need {e.body.get('required')} credits, have {e.body.get('available')}. "
                  "Top up at https://api-dashboard.sloyd.ai and retry; nothing was charged.", file=sys.stderr)
            return 2
        if e.status == 429:
            print("5 jobs are already running on this key. Wait for one to finish, then retry.", file=sys.stderr)
        return 4 if e.status == 401 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
