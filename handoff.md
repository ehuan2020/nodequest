# NodeQuest — Session Handoff

## What We're Building

NodeQuest is a PyQt6 overlay that sits on top of Unreal Engine 5 and guides users through tutorials step-by-step. The overlay panel shows a numbered list of steps; an animated arrow cursor flies to the target UI location in UE5 for each step. The user performs the action manually, then presses Next (or Space) to advance. No automated click detection — fully manual pacing.

---

## Current Architecture

```
main.py
  └── creates QApplication
  └── creates CursorOverlay (cursor.py)
  └── creates OverlayWindow (overlay.py), passes cursor in
  └── shows both windows, runs event loop

overlay.py
  ├── GoalDialog         — frameless dialog for goal input
  ├── CalibrationOverlay — fullscreen one-shot click-capture window
  └── OverlayWindow      — main panel (380px fixed width)
        States: IDLE → LOADING → GUIDING → (back to IDLE)
                IDLE → CALIBRATING → IDLE
                any → ERROR → IDLE

cursor.py  — animated arrow widget, display-only, always click-through
locator.py — reads/writes coordinates.json, resolves anchor → (x, y)
gemini_client.py — calls Gemini API to generate 5-step tutorials
state_machine.py — AppState enum + transition table
worker.py  — QRunnable wrapper for threading Gemini calls
mock_claude.py — fallback step generator if Gemini fails
```

---

## File Status

### `overlay.py`
Complete redesign this session. Key behaviors:
- Fixed width 380px (`setFixedWidth`)
- Header: "NodeQuest" title + X close button
- Goal text shown in small grey under header once goal is set
- Five state panels toggled via `setVisible`: idle / loading / guiding / calibrating / error
- **GUIDING panel**: `QScrollArea` containing step items (max height 340px), Next button, Skip button, "Step X of Y" label
- Each step item is a `QFrame` with: colored circle (grey/blue/green), title label, description label (only visible for current step), left border color indicating state
- `advance_step()` marks current step complete (green ✓), moves to next, cursor flies to new target
- Skip advances without marking complete
- `keyPressEvent` handles Space → `advance_step()`, Escape → `reset_to_idle()`
- Auto-scrolls to keep current step visible via `ensureWidgetVisible`
- Calibration uses `_calib_title_lbl` / `_calib_desc_lbl` in `_calib_panel` (no progress bar)
- **No polling code** — all click detection removed

### `cursor.py`
Display-only. Key behaviors:
- `WA_TransparentForMouseEvents` set — Qt never routes mouse events to it
- `WS_EX_TRANSPARENT` set on `showEvent` — Windows routes OS-level clicks through it
- Animated arrow polygon + pulsing circle at tip
- `move_to(x, y, label)` triggers smooth animation toward target (`_step_toward_target` at 60fps)
- `hide_cursor()` / `show_cursor()` toggle visibility
- `enable_interception()` / `disable_interception()` still exist but are effectively no-ops now
- No `mousePressEvent`, no `forward_click_to_ue5`, no `calibration_click` signal

### `gemini_client.py`
- Prompt instructs Gemini to assume default UE5 layout is open (Content Browser, Details Panel, Outliner, Viewport visible — no steps to open them)
- Anchor restricted to exactly: `Main Toolbar`, `Content Browser`, `Details Panel`, `Outliner`, `Viewport Center`
- Falls back to `mock_claude.generate_steps` on any exception
- **Known issue**: model name is `"gemini-3-flash-preview"` which is probably wrong. Real model names are `gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-2.5-flash-preview-05-20` etc. If Gemini always fails and mock_claude is always used, fix the model name first.

### `locator.py`
- `get_coordinates(anchor)` does case-insensitive exact lookup first
- If not found: keyword fallback cascade with terminal print:
  - "graph" / "editor" → Viewport Center
  - "menu" / "toolbar" / "button" → Main Toolbar
  - "browser" / "content" → Content Browser
  - "detail" / "property" → Details Panel
  - "outline" / "scene" → Outliner
  - anything else → Main Toolbar (last resort)
- No longer falls back to center (1280, 720)

### `coordinates.json`
12 entries total. 5 are live-calibrated on the 2560×1440 display:
- Main Toolbar: (244, 9)
- Content Browser: (1834, 1154)
- Details Panel: (1991, 523)
- Outliner: (2011, 115)
- Viewport Center: (1255, 444)

7 are reasonable defaults (not calibrated):
- Blueprint Graph, Material Graph → same as Viewport Center
- File Menu → (50, 9), Window Menu → (200, 9)
- Add Button, Place Actors → (130, 9)
- Context Menu → (1834, 800)

### `state_machine.py` — unchanged
### `main.py` — unchanged

---

## What Failed — Do Not Retry

1. **Mouse hooks / ctypes for global click detection** — froze the computer entirely. Hard banned.

2. **Removing `WA_TransparentForMouseEvents` from cursor window + custom `mousePressEvent`** — cursor window stole all clicks from UE5 when the user clicked anywhere outside the 120px target radius. UE5 became unusable during tutorial mode.

3. **`GetAsyncKeyState` polling (50ms QTimer in overlay.py)** — was detecting every click anywhere on screen, advancing steps unintentionally. Removed. This is why the current architecture uses manual Next/Space only.

4. **CalibrationOverlay with border-only painting** — old version only painted dark edges, left center unpainted, so clicks in the center (where UE5 panels actually are) fell through. Fixed by `fillRect(self.rect(), ...)` covering every pixel.

5. **Stale `coordinates.json` with y≈9-27 for all panels** — was manually set, didn't match the actual 2560×1440 UE5 layout. Had to reset to `{"calibrated": false}` and run live calibration.

6. **`_check_calibration` only showing a button** — calibration never ran on startup unless the user clicked the button. Fixed by `QTimer.singleShot(500, self._start_calibration)`.

---

## Unused / Vestigial Code to Clean Up Eventually

- `overlay.py` imports `get_ue5_monitor, get_ue5_hwnd` from `monitor_context` — neither is used anywhere in the current code
- `cursor.py` still has `target_clicked = pyqtSignal()` — never emitted (cursor is display-only), never connected
- `cursor.py` `enable_interception()` / `disable_interception()` — still called from calibration path but are no-ops since cursor always has `WS_EX_TRANSPARENT`
- `state_machine.py` has `WAITING_FOR_USER` and `RECOVERY_MODE` states — overlay no longer uses them

---

## Next Steps (in priority order)

1. **Run end-to-end test**: `python main.py` with UE5 open. Type a goal, verify:
   - Gemini returns 5 valid steps (check terminal for `[gemini_client] raw response`)
   - If it always falls back to mock_claude, fix the model name in `gemini_client.py`
   - Step list renders with correct circle colors and descriptions
   - Cursor flies to the calibrated location for step 1
   - Space / Next advances correctly, circle turns green, cursor flies to step 2
   - "Step X of Y" updates correctly

2. **Fix Gemini model name** if Gemini is always failing. Check `gemini_client.py` line with `model=` and replace with a valid model from the Gemini API docs (e.g. `gemini-1.5-flash` or `gemini-2.0-flash-exp`).

3. **Calibrate the 7 default anchors** if they land in wrong places. Recalibration resets all 5 live-calibrated panels — consider adding a way to recalibrate individual panels rather than all 5 at once.

4. **Test the scroll area rendering**: verify step circles are actually round (border-radius on QLabel requires fixed size, which is set to 26×26 — should be fine, but confirm visually).

5. **Consider adding a Home/Reset button** back to the header so users can abort a tutorial mid-way without pressing Escape.
