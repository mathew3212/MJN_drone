import heapq


class GridPlanner:

    def __init__(
        self,
        occupancy_grid,
        cost_map=None,
        hysteresis_threshold=0.5
    ):

        self.grid = occupancy_grid
        self.cost_map = cost_map
        self.hysteresis_threshold = hysteresis_threshold

    def heuristic(self, a, b):

        return (
            abs(a[0] - b[0])
            +
            abs(a[1] - b[1])
        )

    def get_neighbors(self, node):

        x, y = int(round(node[0])), int(round(node[1]))

        neighbors = [

            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1)

        ]

        valid = []

        for nx, ny in neighbors:

            if (
                0 <= nx < self.grid.width
                and
                0 <= ny < self.grid.height
            ):

                if not self.grid.is_obstacle(
                    nx,
                    ny
                ):

                    valid.append(
                        (nx, ny)
                    )

        return valid

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

            for next_node in self.get_neighbors(
                current
            ):

                move_cost = 1

                if self.cost_map:

                    move_cost = self.cost_map.get_cost(
                        next_node[0],
                        next_node[1]
                    )

                new_cost = (
                    cost_so_far[current]
                    +
                    move_cost
                )

                current_cost = cost_so_far.get(
                    next_node
                )

                should_update = (
                    current_cost is None
                    or
                    new_cost
                    <
                    current_cost
                    -
                    self.hysteresis_threshold
                )

                if should_update:

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
    
