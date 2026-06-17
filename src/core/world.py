import random


class DynamicObstacle:

    def __init__(self, x, y):

        self.x = x
        self.y = y

        self.direction = random.choice(
            [
                (1, 0),
                (-1, 0),
                (0, 1),
                (0, -1)
            ]
        )

    def update(self, width, height):

        nx = self.x + self.direction[0]
        ny = self.y + self.direction[1]

        if not (0 <= nx < width):
            self.direction = (
                -self.direction[0],
                self.direction[1]
            )
        else:
            self.x = nx

        if not (0 <= ny < height):
            self.direction = (
                self.direction[0],
                -self.direction[1]
            )
        else:
            self.y = ny


class World:

    def __init__(self, width, height, num_obstacles):

        self.width = width
        self.height = height

        self.obstacles = set()

        self.dynamic_obstacles = [

            DynamicObstacle(20,20),
            DynamicObstacle(20,21),
            DynamicObstacle(20,22),

            DynamicObstacle(50,50),
            DynamicObstacle(50,51),
            DynamicObstacle(50,52),

            DynamicObstacle(70,70),
            DynamicObstacle(70,71),
            DynamicObstacle(70,72)
        ]

        for _ in range(num_obstacles):

            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)

            self.obstacles.add((x, y))

    def is_obstacle(self, x, y):

        if (x, y) in self.obstacles:
            return True

        for obstacle in self.dynamic_obstacles:

            if obstacle.x == x and obstacle.y == y:
                return True

        return False

    def update(self):

        for obstacle in self.dynamic_obstacles:

            obstacle.update(
                self.width,
                self.height
            )