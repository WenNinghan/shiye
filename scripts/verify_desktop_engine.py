"""Run the frozen engine, never the source tree, against a public synthetic sample."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import threading
import queue
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--mode", choices=["document", "academic"], default="document")
    args = parser.parse_args()
    data = Path(args.data).resolve()
    data.mkdir(parents=True, exist_ok=True)
    token, control = secrets.token_hex(32), secrets.token_hex(32)
    env = {**os.environ, "PATH": os.path.join(os.environ["SystemRoot"], "System32")}
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    process = subprocess.Popen([args.engine], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", env=env, cwd=data, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        errors = []
        threading.Thread(target=lambda: [errors.append(line) for line in process.stderr], daemon=True).start()
        process.stdin.write(json.dumps({"token":token,"control":control,"data_dir":str(data)})+"\n")
        process.stdin.close()
        lines = queue.Queue()
        threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
        line = lines.get(timeout=30)
        if not line:
            raise RuntimeError("".join(errors)[-3000:])
        origin = "http://127.0.0.1:"+str(json.loads(line)["port"])
        print("Handshake ready", flush=True)
        with httpx.Client(base_url=origin, headers={"x-shiye-desktop":token}, timeout=5, trust_env=False) as client:
            for _ in range(100):
                try:
                    response = client.get("/api/health")
                    if response.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.2)
            else:
                raise RuntimeError("Health failed: " + "".join(errors)[-3000:])
            print("Health ready", flush=True)
            assert httpx.get(origin+"/api/health", trust_env=False).status_code == 403
            assert client.get("/api/session").status_code == 200
            sample = Path(args.sample)
            response = client.post("/api/documents", files={"files":(sample.name,sample.read_bytes(),"image/png")})
            response.raise_for_status()
            doc = response.json()
            route = "/api/documents/"+doc["id"]
            response = client.post(route+"/start", json={"version":doc["version"],"mode":args.mode})
            response.raise_for_status()
            for _ in range(420 if args.mode == "academic" else 120):
                doc = client.get(route).json()
                if doc["status"] not in ("queued","processing"):
                    break
                time.sleep(1)
            assert doc["status"] == "ready_for_review", doc
            assert any(block["text"] for page in doc["pages"] for block in page["blocks"])
            formulas = [block for page in doc["pages"] for block in page["blocks"] if block["kind"] == "formula"]
            if args.mode == "academic":
                assert formulas, doc["warnings"]
            exported = client.post(route+"/exports", json={"version":doc["version"],"format":"docx"})
            exported.raise_for_status()
            file = client.get(exported.json()["url"])
            assert file.content[:2] == b"PK"
            (data / "sample-export.docx").write_bytes(file.content)
            print(json.dumps({"status":doc["status"],"blocks":sum(len(p["blocks"]) for p in doc["pages"]),
                "formulas":[b["latex"] for b in formulas],
                "docx_bytes":len(file.content),"authentication":True,"no_development_path":True}))
    finally:
        if process.poll() is None:
            subprocess.run(["taskkill.exe","/PID",str(process.pid),"/T","/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        process.wait(timeout=15)


if __name__ == "__main__":
    main()
