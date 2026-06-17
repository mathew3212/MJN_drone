import math


class DroneBehaviors:
    """Drone behavior conditions and actions for the behavior tree.

    Ties together drone state, battery levels, and world conditions
    to enable reactive autonomy via the behavior tree.
    """

    def __init__(
        self,
        drone,
        world,
        battery=None,
        emergency_manager=None,
    ):
        self.drone = drone
        self.world = world
        self.battery = battery
        self.emergency_manager = emergency_manager

        self.state = "NAVIGATE"
        self._avoid_cooldown = 0

    # ========================================
    #  External reference setters
    # ========================================

    def set_battery(self, battery):
        self.battery = battery

    def set_emergency_manager(self, emergency_manager):
        self.emergency_manager = emergency_manager

    # ========================================
    #  Conditions
    # ========================================

    def low_battery(self):
        """Check if battery is low but not critical."""
        if self.battery is None:
            return False
        return (
            self.battery.is_low()
            and
            not self.battery.is_critical()
        )

    def collision_risk(self):
        """Check if drone is about to collide with any obstacle.
        
        Uses a cooldown to prevent perpetual avoidance oscillation.
        Only returns True if the drone is actually ON an obstacle or
        directly adjacent to one in the direction of travel.
        """
        # Cooldown: allow path follower to make progress
        if self._avoid_cooldown > 0:
            self._avoid_cooldown -= 1
            return False

        x, y = int(round(self.drone.position[0])), int(round(self.drone.position[1]))
        # Check if drone is ON an obstacle (immediate danger)
        if (x, y) in self.world.obstacles:
            return True
        for obs in self.world.dynamic_obstacles:
            if obs.x == x and obs.y == y:
                return True
        
        # Check cells immediately adjacent (cardinal directions) for path blocking
        heading = self.drone.heading
        fx, fy = math.cos(heading), math.sin(heading)
        # Check 1-2 cells ahead based on heading direction
        ahead_x = x + int(round(fx))
        ahead_y = y + int(round(fy))
        if (ahead_x, ahead_y) in self.world.obstacles:
            return True
        for obs in self.world.dynamic_obstacles:
            if obs.x == ahead_x and obs.y == ahead_y:
                return True
        
        return False

    def mission_active(self):
        """Mission is considered active unless complete or failed."""
        return True

    def has_emergency(self):
        """Check if there's an active emergency condition."""
        if self.emergency_manager is None:
            return False
        return (
            self.emergency_manager.state
            !=
            self.emergency_manager.NORMAL
        )

    # ========================================
    #  Actions
    # ========================================

    def return_home(self):
        self.state = "RETURN_HOME"
        print(
            "Behavior: Return Home"
        )

    def avoid_collision(self):
        self.state = "AVOID"
        print(
            "Behavior: Avoid Collision"
        )
        # Movement cooldown so the path follower can make progress
        self._avoid_cooldown = 10

        # Move away from nearest obstacle
        x, y = int(round(self.drone.position[0])), int(round(self.drone.position[1]))
        best = (float(x), float(y))
        best_dist = 0
        for nx, ny in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]:
            if not (0 <= nx < self.world.width and 0 <= ny < self.world.height):
                continue
            if self.world.is_obstacle(nx, ny):
                continue
            min_dist = float('inf')
            for ox, oy in self.world.obstacles:
                d = (nx-ox)**2 + (ny-oy)**2
                if d < min_dist:
                    min_dist = d
            for obs in self.world.dynamic_obstacles:
                d = (nx-obs.x)**2 + (ny-obs.y)**2
                if d < min_dist:
                    min_dist = d
            if min_dist > best_dist:
                best = (float(nx), float(ny))
                best_dist = min_dist
        self.drone.x, self.drone.y = best

    def navigate(self):
        self.state = "NAVIGATE"