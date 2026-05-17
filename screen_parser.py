import subprocess, json, mss, os, time, tempfile, threading
from PIL import Image

OMNI_PYTHON = r'D:\Nodequest\OmniParser\omni\Scripts\python.exe'
OMNI_SERVER = r'D:\Nodequest\omni_server.py'
REQUEST_FILE = 'D:/Nodequest/omni_request.json'
RESULT_FILE = 'D:/Nodequest/omni_result.json'
READY_FILE = 'D:/Nodequest/omni_ready.txt'

_server_process = None
_server_ready = False


def start_server():
    global _server_process, _server_ready
    if _server_process is not None:
        return
    for f in [REQUEST_FILE, RESULT_FILE, READY_FILE]:
        if os.path.exists(f):
            os.remove(f)
    print('[OmniParser] Starting server...')
    _server_process = subprocess.Popen(
        [OMNI_PYTHON, OMNI_SERVER],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    )

    def print_output():
        for line in _server_process.stdout:
            print(f'[OmniServer] {line.rstrip()}')

    threading.Thread(target=print_output, daemon=True).start()

    print('[OmniParser] Waiting for models to load...')
    timeout = 300
    start = time.time()
    last_progress = start
    while not os.path.exists(READY_FILE):
        now = time.time()
        if now - start > timeout:
            print('[OmniParser] Timeout waiting for server')
            return
        if now - last_progress >= 10:
            print('[OmniParser] Still loading models, please wait...')
            last_progress = now
        time.sleep(0.5)
    _server_ready = True
    print('[OmniParser] Server ready')


def load_models():
    threading.Thread(target=start_server, daemon=True).start()


def take_screenshot() -> Image.Image:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        return Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')


def find_element(target: str, screenshot: Image.Image = None) -> tuple[float, float] | None:
    if not _server_ready:
        print('[OmniParser] Server not ready yet')
        return None
    try:
        if screenshot is None:
            screenshot = take_screenshot()
        temp_img = tempfile.mktemp(suffix='.png', dir='D:/Nodequest')
        screenshot.save(temp_img)
        with open(REQUEST_FILE, 'w') as f:
            json.dump({'img_path': temp_img, 'target': target}, f)
        start = time.time()
        while True:
            if time.time() - start > 60:
                print('[OmniParser] Timeout')
                return None
            if os.path.exists(RESULT_FILE):
                try:
                    time.sleep(0.05)
                    with open(RESULT_FILE) as f:
                        result = json.load(f)
                    try:
                        os.remove(RESULT_FILE)
                    except Exception:
                        pass
                    break
                except (json.JSONDecodeError, PermissionError):
                    time.sleep(0.1)
                    continue
            time.sleep(0.05)
        try:
            os.remove(temp_img)
        except Exception:
            pass
        if result.get('found'):
            x, y = result['x'], result['y']
            print(f'[OmniParser] Found {target} at ({x:.0f},{y:.0f})')
            return float(x), float(y)
        return None
    except Exception as e:
        print(f'[OmniParser] Error: {e}')
        return None
