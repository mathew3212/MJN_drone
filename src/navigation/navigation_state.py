class NavigationState:

    def __init__(self):

        self.path = None

        self.current_waypoint = 1

        self.path_valid = False

    def reset_path(

        self,

        path

    ):

        self.path = path

        self.current_waypoint = 1

        self.path_valid = (
            path is not None
        )

    def current_target(self):

        if (

            self.path is None

            or

            self.current_waypoint
            >=
            len(self.path)

        ):

            return None

        return self.path[
            self.current_waypoint
        ]

    def advance(self):

        self.current_waypoint += 1