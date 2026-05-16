from enum import Enum


class AppState(Enum):
    IDLE = "IDLE"
    LOADING = "LOADING"
    GUIDING = "GUIDING"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    RECOVERY_MODE = "RECOVERY_MODE"
    ERROR = "ERROR"
    CALIBRATING = "CALIBRATING"


VALID_TRANSITIONS: dict[AppState, list[AppState]] = {
    AppState.IDLE:             [AppState.LOADING, AppState.CALIBRATING],
    AppState.LOADING:          [AppState.GUIDING, AppState.ERROR],
    AppState.GUIDING:          [AppState.WAITING_FOR_USER, AppState.RECOVERY_MODE, AppState.ERROR],
    AppState.WAITING_FOR_USER: [AppState.GUIDING, AppState.IDLE],
    AppState.RECOVERY_MODE:    [AppState.WAITING_FOR_USER, AppState.ERROR],
    AppState.ERROR:            [AppState.IDLE],
    AppState.CALIBRATING:      [AppState.IDLE],
}


class StateMachine:
    def __init__(self):
        self.current_state = AppState.IDLE

    def set_state(self, new_state: AppState):
        if new_state not in VALID_TRANSITIONS.get(self.current_state, []):
            print(f"WARNING: Invalid transition {self.current_state.value} -> {new_state.value}")
        print(f"State: {self.current_state.value} -> {new_state.value}")
        self.current_state = new_state

    def get_state(self) -> AppState:
        return self.current_state

    def is_state(self, state: AppState) -> bool:
        return self.current_state == state

    def reset(self):
        self.set_state(AppState.IDLE)
