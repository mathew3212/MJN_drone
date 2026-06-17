class OccupancyGrid:

    UNKNOWN = -1
    FREE = 0
    OCCUPIED = 1

    def __init__(
        self,
        width,
        height
    ):

        self.width = width
        self.height = height

        self.grid = [

            [
                self.UNKNOWN
                for _ in range(width)
            ]

            for _ in range(height)

        ]

    def mark_obstacle(
        self,
        x,
        y
    ):

        ix = int(round(x))
        iy = int(round(y))
        self.grid[iy][ix] = self.OCCUPIED

    def mark_free(
        self,
        x,
        y
    ):

        ix = int(round(x))
        iy = int(round(y))
        if 0 <= ix < self.width and 0 <= iy < self.height:
            self.grid[iy][ix] = self.FREE

    def is_obstacle(
        self,
        x,
        y
    ):

        ix = int(round(x))
        iy = int(round(y))
        return (
            self.grid[iy][ix]
            ==
            self.OCCUPIED
        )

    def update_from_scan(
        self,
        visible_obstacles,
        drone_x,
        drone_y,
        radius
    ):

        # Mark cells near the drone as explored

        for y in range(self.height):

            for x in range(self.width):

                dx = x - drone_x
                dy = y - drone_y

                distance = (
                    dx * dx +
                    dy * dy
                ) ** 0.5

                if distance <= radius:

                    self.mark_free(
                        x,
                        y
                    )

        # Mark detected obstacles

        for x, y in visible_obstacles:

            self.mark_obstacle(
                x,
                y
            )