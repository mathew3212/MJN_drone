class SensorEngine:

    def __init__(self, scan_radius=8):

        self.scan_radius = scan_radius

    def scan(
        self,
        drone,
        world
    ):

        visible_obstacles = []

        for ox, oy in world.obstacles:

            dx = ox - drone.x
            dy = oy - drone.y

            distance = (
                dx * dx +
                dy * dy
            ) ** 0.5

            if distance <= self.scan_radius:

                visible_obstacles.append(
                    (ox, oy)
                )

        return visible_obstacles