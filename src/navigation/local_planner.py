import math
from collections import deque


class LocalPlanner:

    def __init__(

        self,

        lookahead_distance=5,

        corridor_radius=4,

        stuck_threshold=0.5,

        stuck_frames=20,

        replan_cooldown=30

    ):

        self.lookahead_distance = (
            lookahead_distance
        )

        self.corridor_radius = (
            corridor_radius
        )

        self.stuck_threshold = (
            stuck_threshold
        )

        self.stuck_frames = (
            stuck_frames
        )

        self.replan_cooldown = (
            replan_cooldown
        )

        self.position_history = deque(
            maxlen=stuck_frames
        )

        self.cooldown_counter = 0

    # =====================================
    # Distance
    # =====================================

    def distance(

        self,

        a,

        b

    ):

        return math.sqrt(

            (a[0] - b[0]) ** 2

            +

            (a[1] - b[1]) ** 2

        )

    # =====================================
    # Path Pruning
    # =====================================

    def prune_path(

        self,

        path,

        drone_position

    ):

        if not path:

            return path

        best_index = 0

        best_distance = float(
            "inf"
        )

        for i, waypoint in enumerate(
            path
        ):

            d = self.distance(

                waypoint,

                drone_position

            )

            if d < best_distance:

                best_distance = d

                best_index = i

        return path[
            best_index:
        ]

    # =====================================
    # Lookahead Target
    # =====================================

    def get_lookahead_target(

        self,

        path

    ):

        if not path:

            return None

        index = min(

            self.lookahead_distance,

            len(path) - 1

        )

        return path[index]

    # =====================================
    # Corridor Check
    # =====================================

    def inside_corridor(

        self,

        drone_position,

        path

    ):

        if not path:

            return False

        nearest = min(

            self.distance(
                drone_position,
                p
            )

            for p in path

        )

        return (

            nearest
            <=
            self.corridor_radius

        )

    # =====================================
    # Stuck Detection
    # =====================================

    def update_stuck_detector(

        self,

        drone_position

    ):

        self.position_history.append(
            drone_position
        )

        if (

            len(
                self.position_history
            )

            <
            self.stuck_frames

        ):

            return False

        start = (
            self.position_history[0]
        )

        end = (
            self.position_history[-1]
        )

        movement = self.distance(
            start,
            end
        )

        return (

            movement
            <
            self.stuck_threshold

        )

    # =====================================
    # Replan Cooldown
    # =====================================

    def allow_replan(

        self

    ):

        if (
            self.cooldown_counter
            <= 0
        ):

            self.cooldown_counter = (
                self.replan_cooldown
            )

            return True

        self.cooldown_counter -= 1

        return False

    # =====================================
    # Main Update
    # =====================================

    def update(

        self,

        drone_position,

        global_path

    ):

        if not global_path:

            return None

        pruned_path = self.prune_path(

            global_path,

            drone_position

        )

        target = (

            self.get_lookahead_target(
                pruned_path
            )

        )

        return target