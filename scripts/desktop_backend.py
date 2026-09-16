"""Private desktop entry point. Secrets arrive on stdin, never argv or a URL."""
import multiprocessing
import sys


def main():
    import json
    import os
    import socket
    import threading
    from pathlib import Path
    import uvicorn

    if not getattr(sys, "frozen", False):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    raw = sys.stdin.readline(32769)
    if len(raw) > 32768:
        raise ValueError("Invalid desktop handshake")
    options = json.loads(raw)
    for name in ("token", "control"):
        if not isinstance(options.get(name), str) or len(options[name]) < 40:
            raise ValueError("Invalid desktop token")
    data = Path(options["data_dir"]).resolve()
    # All temporary application data remains outside read-only installation assets.
    os.environ["SHIYE_DATA_DIR"] = str(data)
    from shiye.config import Settings
    from shiye.main import create_app

    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    settings = Settings(data_dir=data, web_dir=root / "web" / "dist",
                        desktop_token=options["token"], control_token=options["control"],
                        desktop_host=f"127.0.0.1:{port}")
    app = create_app(settings)
    print(json.dumps({"port": port}), flush=True)
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        parent = kernel.OpenProcess(0x00100000, False, os.getppid())
        if not parent:
            raise OSError("Cannot establish desktop lifetime monitor")
        def parent_watch():
            # A process handle avoids keeping stdin open across multiprocessing.
            result = kernel.WaitForSingleObject(parent, 0xFFFFFFFF)
            kernel.CloseHandle(parent)
            if result == 0:
                server.should_exit = True
        threading.Thread(target=parent_watch, daemon=True).start()
    server.run(sockets=[listener])


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
