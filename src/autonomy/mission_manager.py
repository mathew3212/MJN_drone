import math

class MissionManager:

    GO_TO_TARGET = "GO_TO_TARGET"
    INSPECT_TARGET = "INSPECT_TARGET"
    RETURN_HOME = "RETURN_HOME"
    LAND = "LAND"
    COMPLETE = "COMPLETE"

    def __init__(
        self,
        home_position,
        target_position
    ):

        self.home_position = (
            home_position
        )

        self.target_position = (
            target_position
        )

        self.state = (
            self.GO_TO_TARGET
        )

        self.inspection_timer = 0

    # ==========================
    # Current Goal
    # ==========================

    def get_current_goal(self):

        if self.state == self.GO_TO_TARGET:

            return self.target_position

        if self.state == self.RETURN_HOME:

            return self.home_position

        return None

    # ==========================
    # State Updates
    # ==========================

    def update(
        self,
        drone_position
    ):
        # Calculate Euclidean distance to current target for robustness
        target = self.get_current_goal()
        dist = math.sqrt((drone_position[0]-target[0])**2 + (drone_position[1]-target[1])**2) if target else float('inf')

        if (
            self.state
            ==
            self.GO_TO_TARGET
            and (dist < 1.5)

        ):

            print(
                "\nTarget reached."
            )

            print(
                "Starting inspection..."
            )

            self.state = (
                self.INSPECT_TARGET
            )

            self.inspection_timer = 50

        elif (

            self.state
            ==
            self.INSPECT_TARGET

        ):

            self.inspection_timer -= 1

            if self.inspection_timer <= 0:

                print(
                    "\nInspection complete."
                )

                print(
                    "Returning Home..."
                )

                self.state = (
                    self.RETURN_HOME
                )

        elif (

            self.state
            ==
            self.RETURN_HOME

            and
            # Use distance-based check for float positions
            math.sqrt((drone_position[0] - self.home_position[0])**2 + (drone_position[1] - self.home_position[1])**2) < 1.5

        ):

            print(
                "\nHome reached."
            )

            print(
                "Landing..."
            )

            self.state = self.LAND

        elif self.state == self.LAND:

            print(
                "\nMission Complete."
            )

            self.state = (
                self.COMPLETE
            )

    # ==========================
    # Status
    # ==========================

    def is_complete(self):

        return (

            self.state
            ==
            self.COMPLETE

        )