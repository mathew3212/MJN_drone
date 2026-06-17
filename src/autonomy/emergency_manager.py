class EmergencyManager:

    NORMAL = "NORMAL"

    LOW_BATTERY = "LOW_BATTERY"

    CRITICAL_BATTERY = (
        "CRITICAL_BATTERY"
    )

    NO_PATH = "NO_PATH"

    STUCK = "STUCK"

    SENSOR_FAILURE = (
        "SENSOR_FAILURE"
    )

    EMERGENCY_LAND = (
        "EMERGENCY_LAND"
    )

    def __init__(self):

        self.state = self.NORMAL

        self.last_position = None

    # ==========================
    # Main Evaluation
    # ==========================

    def evaluate(

        self,

        drone,

        battery,

        path,

        sensor_ok=True

    ):

        # ----------------------
        # Critical Battery
        # ----------------------

        if battery.is_critical():

            self.state = (
                self.CRITICAL_BATTERY
            )

            return self.state

        # ----------------------
        # Low Battery
        # ----------------------

        if battery.is_low():

            self.state = (
                self.LOW_BATTERY
            )

            return self.state

        # ----------------------
        # No Path
        # ----------------------

        if path is None:

            self.state = (
                self.NO_PATH
            )

            return self.state

        # ----------------------
        # Sensor Failure
        # ----------------------

        if not sensor_ok:

            self.state = (
                self.SENSOR_FAILURE
            )

            return self.state

        # ----------------------
        # Stuck detection is now handled by local_planner and main loop
        # The emergency_manager.STUCK state will be set by the main loop if local_planner detects stuck.
        # ----------------------
        self.state = self.NORMAL # If no other emergency, return to normal
        return self.state