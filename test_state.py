from state_machine import StateMachine, AppState
from models import TutorialStep, CoordinateResult

print("=== State Machine ===")
sm = StateMachine()
sm.set_state(AppState.LOADING)
sm.set_state(AppState.GUIDING)
sm.set_state(AppState.WAITING_FOR_USER)
sm.set_state(AppState.IDLE)

print("\n--- Invalid transition ---")
sm.set_state(AppState.LOADING)   # valid: IDLE -> LOADING
sm.set_state(AppState.ERROR)     # valid: LOADING -> ERROR
sm.set_state(AppState.GUIDING)   # INVALID: ERROR can only go to IDLE

print("\n=== Pydantic Models ===")
step = TutorialStep(
    step_number=1,
    title="Open Content Browser",
    description="Click the Content Browser tab at the bottom of the screen",
    action="left-click",
    anchor="Content Browser",
    relative_position="tab",
    recovery_hint="Go to the Window menu at the top of the screen and select Content Browser from the list",
    recovery_anchor="Main Toolbar",
)
print(f"TutorialStep: {step}")
print(f"recovery_hint (truncated): {step.recovery_hint!r}")

coord = CoordinateResult(x=400.0, y=850.0, confidence="high")
print(f"CoordinateResult: {coord}")
