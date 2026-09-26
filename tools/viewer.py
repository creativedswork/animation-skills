#!/usr/bin/env python3
"""Serve the local Three.js viewer and explicitly listed GLB artifacts."""

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import project


def catalog(root):
    assets = project.load(root / "assets.json")
    resources, sources = {}, {}

    def model(key, label, kind, artifact, verdict="pending"):
        path = project.local_path(root, artifact["path"], ".artifacts")
        available = path.is_file() and project.file_hash(path) == artifact["sha256"]
        if available:
            resources[key] = path
        return {"id": key, "label": label, "kind": kind, "verdict": verdict,
                "available": available, "url": "/models/" + key if available else None}

    for asset_id, asset in assets.items():
        if Path(asset["path"]).suffix.lower() == ".glb":
            sources[asset_id] = model("input-" + asset_id, "固定输入 · 源素材", "source", asset)
    cases = []
    for path in sorted((root / "cases").glob("*/case.json")):
        case = project.load(path)
        case["models"] = [sources[key] for key in case["inputs"] if key in sources]
        case["run_count"] = 0
        for run_path in sorted((path.parent / "runs").glob("*.json")):
            run = project.load(run_path)
            case["run_count"] += 1
            for version, label in (("initial", "初稿"), ("corrected", "修正版")):
                result = run.get(version)
                if result is None:
                    continue
                for index, artifact in enumerate(result["artifacts"]):
                    if artifact["role"] == "export" and Path(artifact["path"]).suffix.lower() == ".glb":
                        key = "{}-{}-{}-{}".format(case["id"], run["id"], version, index)
                        verdict = result["review"]["verdict"] if run["status"] == "reviewed" else "pending"
                        case["models"].append(model(key, run["id"] + " · " + label, version, artifact, verdict))
        cases.append(case)
    return {"cases": cases}, resources


def handler_for(root):
    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body=b"", content_type="text/plain; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            route = unquote(urlsplit(self.path).path)
            try:
                if route == "/api/cases":
                    payload, _ = catalog(root)
                    self.send(200, json.dumps(payload, ensure_ascii=False).encode(),
                              "application/json; charset=utf-8")
                    return
                if route.startswith("/models/"):
                    _, resources = catalog(root)
                    path = resources.get(route[len("/models/"):])
                    if path is None:
                        self.send(404, b"Model missing or fingerprint mismatch")
                        return
                elif route == "/":
                    path = root / "viewer/index.html"
                elif route.startswith("/viewer/"):
                    path = project.local_path(root, route[1:], "viewer")
                elif route.startswith("/vendor/three/"):
                    relative = "node_modules/three/" + route[len("/vendor/three/"):]
                    path = project.local_path(root, relative, "node_modules/three")
                elif route == "/favicon.ico":
                    self.send(204)
                    return
                else:
                    self.send(404, b"Not found")
                    return
                if not path.is_file():
                    self.send(404, b"Not found")
                    return
                content_type = {".js": "text/javascript", ".glb": "model/gltf-binary"}.get(
                    path.suffix, mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                self.send(200, path.read_bytes(), content_type)
            except (ValueError, KeyError, TypeError, OSError):
                self.send(400, b"Could not read viewer data; run python3 tools/project.py check --artifacts")

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    root = project.ROOT
    if not (root / "node_modules/three/build/three.module.js").is_file():
        parser.exit(1, "Three.js is missing. Run npm ci in the repository first.\n")
    project.check(root)
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(root)) as server:
        print("Animation Skills viewer: http://127.0.0.1:{}".format(server.server_port), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
