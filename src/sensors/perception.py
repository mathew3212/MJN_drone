class PerceptionEngine:

    def process(
        self,
        drone,
        target,
        obstacles
    ):

        perception = {

            "target_dx":
            target[0] - drone.x,

            "target_dy":
            target[1] - drone.y,

            "obstacles":
            obstacles
        }

        return perception