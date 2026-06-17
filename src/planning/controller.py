class Controller:

    def execute(
        self,
        drone,
        action,
        world
    ):

        nx = drone.x + action[0]
        ny = drone.y + action[1]

        if world.is_obstacle(
            nx,
            ny
        ):
            print(
                f"BLOCKED at {(nx, ny)}"
            )
            return False

        drone.move(
            action[0],
            action[1]
        )

        return True