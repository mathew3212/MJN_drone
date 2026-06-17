import math


class LocalPlanner:

    def __init__(

        self,

        obstacle_radius=3

    ):

        self.obstacle_radius = (
            obstacle_radius
        )

    def choose_next_step(

        self,

        drone,

        target,

        world

    ):

        tx, ty = target

        candidates = [

            (1, 0),

            (-1, 0),

            (0, 1),

            (0, -1),

            (1, 1),

            (-1, -1),

            (1, -1),

            (-1, 1)

        ]

        best_score = float("inf")

        best_pos = (
            drone.x,
            drone.y
        )

        for dx, dy in candidates:

            nx = drone.x + dx
            ny = drone.y + dy

            if world.is_obstacle(
                nx,
                ny
            ):
                continue

            distance = math.sqrt(

                (tx - nx) ** 2
                +

                (ty - ny) ** 2

            )

            obstacle_penalty = 0

            for obs in (
                world.dynamic_obstacles
            ):

                d = math.sqrt(

                    (obs.x - nx) ** 2
                    +

                    (obs.y - ny) ** 2

                )

                if d < self.obstacle_radius:

                    obstacle_penalty += (
                        50 / max(d, 0.1)
                    )

            score = (
                distance
                +
                obstacle_penalty
            )

            if score < best_score:

                best_score = score

                best_pos = (
                    nx,
                    ny
                )

        return best_pos