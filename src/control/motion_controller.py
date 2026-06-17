class MotionController:

    def __init__(self):

        self.active = True

    def update(

        self,

        path_follower,

        drone,

        waypoint

    ):

        if not self.active:

            return True

        return path_follower.follow(

            drone,

            waypoint

        )