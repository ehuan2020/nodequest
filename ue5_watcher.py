import unreal
import os
import json

COMMAND_FILE = "D:/nodequest/ue5_command.py"
RESULT_FILE = "D:/nodequest/ue5_result.json"


def check_for_command():
    if os.path.exists(COMMAND_FILE):
        try:
            with open(COMMAND_FILE) as f:
                code = f.read()
            os.remove(COMMAND_FILE)
            exec(code, {"unreal": unreal})
            print("[NodeQuest] Command executed")
        except Exception as e:
            with open(RESULT_FILE, "w") as f:
                json.dump({"error": str(e)}, f)
            print(f"[NodeQuest] Command error: {e}")


print("[NodeQuest] Watcher loaded")
print(f"[NodeQuest] Watching for: {COMMAND_FILE}")
print("[NodeQuest] Call check_for_command() to poll, or run the ticker below.")

# Tick-based approach using a slate post-tick callback.
# unreal.register_slate_post_tick_callback fires every editor frame (~60fps).
# We throttle to ~1 check/second using a counter.
_tick_counter = [0]
_TICK_INTERVAL = 60  # roughly 1 second at 60fps


def _on_tick(delta_seconds: float):
    _tick_counter[0] += 1
    if _tick_counter[0] >= _TICK_INTERVAL:
        _tick_counter[0] = 0
        check_for_command()


try:
    _ticker_handle = unreal.register_slate_post_tick_callback(_on_tick)
    print("[NodeQuest] Tick registered — watcher is active.")
except Exception as e:
    print(f"[NodeQuest] Could not register tick: {e}")
    print("[NodeQuest] Call check_for_command() manually to poll.")
