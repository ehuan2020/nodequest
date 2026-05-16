import unreal
import json
import os


def get_editor_panel_positions():
    positions = {}

    try:
        asset_subsystem = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
        open_assets = asset_subsystem.get_all_edited_assets()
        print(f"Open assets: {len(open_assets)}")
    except Exception as e:
        print(f"Error: {e}")

    output_path = "D:/nodequest/ue5_panels.json"
    with open(output_path, "w") as f:
        json.dump(positions, f, indent=2)

    print(f"Written to {output_path}")
    return positions


get_editor_panel_positions()
