import heapq


class AStarPlanner:

    def __init__(self, world):
        self.world = world

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_neighbors(self, node):

        x, y = node

        neighbors = [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1)
        ]

        valid = []

        for nx, ny in neighbors:

            if nx < 0 or nx >= self.world.width:
                continue

            if ny < 0 or ny >= self.world.height:
                continue

            if self.world.is_obstacle(nx, ny):
                continue

            valid.append((nx, ny))

        return valid

    def find_path(self, start, goal):

        open_set = []

        heapq.heappush(
            open_set,
            (0, start)
        )

        came_from = {}

        g_score = {
            start: 0
        }

        while open_set:

            _, current = heapq.heappop(
                open_set
            )

            if current == goal:

                path = []

                while current in came_from:

                    path.append(current)

                    current = came_from[current]

                path.append(start)

                path.reverse()

                return path

            for neighbor in self.get_neighbors(
                current
            ):

                tentative_g = (
                    g_score[current] + 1
                )

                if (
                    neighbor not in g_score
                    or
                    tentative_g < g_score[neighbor]
                ):

                    came_from[neighbor] = current

                    g_score[neighbor] = tentative_g

                    f_score = (
                        tentative_g
                        +
                        self.heuristic(
                            neighbor,
                            goal
                        )
                    )

                    heapq.heappush(
                        open_set,
                        (
                            f_score,
                            neighbor
                        )
                    )

        return None