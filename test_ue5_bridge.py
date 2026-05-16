import os
import time
from ue5_client import send_command, get_panel_positions, COMMAND_FILE, RESULT_FILE

print("=" * 50)
print("NodeQuest file-based bridge test")
print("=" * 50)
print()
print("PREREQUISITE: ue5_watcher.py must be running inside UE5.")
print("In the UE5 Python console run:")
print("  exec(open(r'D:/nodequest/ue5_watcher.py').read())")
print()
input("Press Enter when the watcher is loaded in UE5...")

print()
print("=" * 50)
print("1. Sending a simple print command...")
result = send_command(
    "import json\n"
    "with open('D:/nodequest/ue5_result.json', 'w') as f:\n"
    "    json.dump({'status': 'hello from UE5'}, f)\n"
)
print(f"Result: {result}")

print()
print("=" * 50)
print("2. Fetching UE5 version via get_panel_positions()...")
positions = get_panel_positions()
print(f"Result: {positions}")

print()
print("=" * 50)
print("Done.")
if "error" in result or "error" in positions:
    print("At least one command failed — check that the watcher tick is running in UE5.")
else:
    print("Both commands succeeded. File-based bridge is working.")
