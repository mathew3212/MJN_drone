import heapq


class DStarLite:

    def __init__(
        self,
        occupancy_grid
    ):

        self.grid = occupancy_grid

    def heuristic(
        self,
        a,
        b
    ):

        return (
            abs(a[0] - b[0])
            +
            abs(a[1] - b[1])
        )

    def find_path(
        self,
        start,
        goal
    ):

        # Convert continuous coordinates to discrete grid indices
        start = (int(round(start[0])), int(round(start[1])))
        goal = (int(round(goal[0])), int(round(goal[1])))

        frontier = []

        heapq.heappush(
            frontier,
            (0, start)
        )

        came_from = {
            start: None
        }

        cost_so_far = {
            start: 0
        }

        while frontier:

            current = heapq.heappop(
                frontier
            )[1]

            if current == goal:
                break

            x, y = current

            neighbors = [

                (x + 1, y),
                (x - 1, y),
                (x, y + 1),
                (x, y - 1)

            ]

            for nx, ny in neighbors:

                if (
                    nx < 0
                    or ny < 0
                    or nx >= self.grid.width
                    or ny >= self.grid.height
                ):
                    continue

                if self.grid.is_obstacle(
                    nx,
                    ny
                ):
                    continue

                new_cost = (
                    cost_so_far[current]
                    + 1
                )

                next_node = (
                    nx,
                    ny
                )

                if (
                    next_node not in cost_so_far
                    or
                    new_cost <
                    cost_so_far[next_node]
                ):

                    cost_so_far[
                        next_node
                    ] = new_cost

                    priority = (
                        new_cost
                        +
                        self.heuristic(
                            goal,
                            next_node
                        )
                    )

                    heapq.heappush(
                        frontier,
                        (
                            priority,
                            next_node
                        )
                    )

                    came_from[
                        next_node
                    ] = current

        if goal not in came_from:
            return None

        path = []

        current = goal

        while current is not None:

            path.append(
                current
            )

            current = came_from[
                current
            ]

        path.reverse()

        return path