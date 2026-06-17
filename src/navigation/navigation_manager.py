class NavigationManager:

    def __init__(

        self,

        planner,

        path_follower,

        motion_controller,

        navigation_state

    ):

        self.planner = planner

        self.path_follower = (
            path_follower
        )

        self.motion_controller = (
            motion_controller
        )

        self.navigation_state = (
            navigation_state
        )

    def replan(

        self,

        start,

        goal

    ):

        path = self.planner.find_path(

            start,

            goal

        )

        self.navigation_state.reset_path(
            path
        )

        return path

    def update(

        self,

        drone

    ):

        waypoint = (
            self.navigation_state
            .current_target()
        )

        if waypoint is None:

            return True

        reached = (

            self.motion_controller
            .update(

                self.path_follower,

                drone,

                waypoint

            )

        )

        if reached:

            self.navigation_state.advance()

        return False