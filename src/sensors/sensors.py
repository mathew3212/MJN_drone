import math


class SensorEngine:

    def __init__(self, sensor_range=15):
        self.sensor_range = sensor_range

    def scan(self, drone, world):

        nearby_obstacles = []

        for obs in world.obstacles:

            dx = obs[0] - drone.x
            dy = obs[1] - drone.y

            distance = math.sqrt(dx**2 + dy**2)

            if distance <= self.sensor_range:

                nearby_obstacles.append(
                    {
                        "position": obs,
                        "distance": distance
                    }
                )

        return nearby_obstacles