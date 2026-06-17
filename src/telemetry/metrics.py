from collections import deque


class Metrics:

    def __init__(self):

        self.steps = 0
        self.replans = 0
        self.obstacles_seen = 0

        self.total_distance_travelled = 0.0
        self.target_reach_step = -1
        self.return_home_step = -1
        self.stuck_events = [] # Stores (step, position)
        self.path_lengths = []

        # For NAVIGATION_REPORT.md
        self.path_history = deque(maxlen=100) # Store last 100 positions for detection
        self.speed_history = deque(maxlen=10) # Store last 10 speeds for slowdown detection
        self.oscillation_events = [] # Stores (step, position, cause, fix)
        self.orbiting_events = [] # Stores (step, position, cause, fix)
        self.path_loop_events = [] # Stores (step, position, cause, fix)
        self.slowdown_events = [] # Stores (step, current_speed, cause, fix)
        self.problems = [] # General list for all detected problems

    def update(
        self,
        path_length,
        visible_obstacles,
        drone_position, # New parameter
        drone_speed # New parameter
    ):
        self.steps += 1
        # self.replans is now incremented in main.py when a replan is triggered
        self.obstacles_seen += visible_obstacles
        self.path_lengths.append(path_length)

        # Update history for detection
        self.path_history.append(drone_position)
        self.speed_history.append(drone_speed)

        # Run detection methods
        self.detect_oscillation(drone_position)
        self.detect_orbiting(drone_position)
        self.detect_path_loops(drone_position)
        self.detect_slowdowns(drone_speed)

    def average_path_length(self):
        if not self.path_lengths:
            return 0
        return (
            sum(self.path_lengths)
            /
            len(self.path_lengths)
        )

    def direct_distance(self, start, end):
        return ((start[0] - end[0])**2 + (start[1] - end[1])**2)**0.5

    def calculate_target_reach_time(self):
        return self.target_reach_step if self.target_reach_step != -1 else "N/A"

    def calculate_return_home_time(self):
        # Assuming return home time is from mission start to home reached
        return self.return_home_step if self.return_home_step != -1 else "N/A"

    def calculate_path_efficiency(self, start_pos, target_pos):
        if self.total_distance_travelled == 0:
            return 0.0
        direct_dist = self.direct_distance(start_pos, target_pos)
        return (direct_dist / self.total_distance_travelled) * 100

    def calculate_average_speed(self):
        if self.steps == 0:
            return 0.0
        # Assuming each step is a unit of time
        return self.total_distance_travelled / self.steps

    def detect_oscillation(self, current_position, history_len=5, tolerance=0.5):
        if len(self.path_history) < history_len:
            return

        recent_positions = list(self.path_history)[-history_len:]
        unique_recent_positions = []
        for pos in recent_positions:
            if not any(self.direct_distance(pos, up) < tolerance for up in unique_recent_positions):
                unique_recent_positions.append(pos)

        # Simple oscillation: alternating between 2 points
        if len(unique_recent_positions) == 2:
            # Check if it's actually alternating
            alternating = True
            for i in range(history_len - 2):
                dist1 = self.direct_distance(recent_positions[i], unique_recent_positions[0])
                dist2 = self.direct_distance(recent_positions[i], unique_recent_positions[1])
                if (dist1 < tolerance and self.direct_distance(recent_positions[i+1], unique_recent_positions[1]) < tolerance) or \
                   (dist2 < tolerance and self.direct_distance(recent_positions[i+1], unique_recent_positions[0]) < tolerance):
                    continue
                else:
                    alternating = False
                    break
            if alternating and (self.steps, current_position) not in [(e[0], e[1]) for e in self.oscillation_events]:
                self.oscillation_events.append((self.steps, current_position, "Drone alternating between two points.", "Adjust local planner parameters or path smoothing."))
                self.problems.append(f"Oscillation detected at step {self.steps} at {current_position}.")

    def detect_orbiting(self, current_position, history_len=10, radius_threshold=2.0, movement_threshold=0.5):
        if len(self.path_history) < history_len:
            return

        recent_positions = list(self.path_history)[-history_len:]
        # Check if all recent positions are within a small radius of their mean
        mean_x = sum(p[0] for p in recent_positions) / history_len
        mean_y = sum(p[1] for p in recent_positions) / history_len
        center = (mean_x, mean_y)

        all_within_radius = all(self.direct_distance(p, center) < radius_threshold for p in recent_positions)
        # Ensure there's actual movement, not just stuck
        total_movement_in_history = sum(self.direct_distance(recent_positions[i], recent_positions[i+1]) for i in range(history_len - 1))

        if all_within_radius and total_movement_in_history > movement_threshold and \
           (self.steps, current_position) not in [(e[0], e[1]) for e in self.orbiting_events]:
            self.orbiting_events.append((self.steps, current_position, "Drone moving in a circular pattern without significant progress.", "Re-evaluate local planning and obstacle avoidance logic."))
            self.problems.append(f"Orbiting detected at step {self.steps} at {current_position}.")

    def detect_path_loops(self, current_position, loop_length=10, tolerance=1.0):
        if len(self.path_history) < 2 * loop_length:
            return

        recent_segment = list(self.path_history)[-loop_length:]
        # Compare recent segment with earlier segments
        for i in range(len(self.path_history) - 2 * loop_length):
            earlier_segment = list(self.path_history)[i : i + loop_length]
            if len(earlier_segment) != loop_length:
                continue

            # Check if segments are similar (e.g., average distance between corresponding points is small)
            avg_dist = sum(self.direct_distance(recent_segment[j], earlier_segment[j]) for j in range(loop_length)) / loop_length
            if avg_dist < tolerance and (self.steps, current_position) not in [(e[0], e[1]) for e in self.path_loop_events]:
                self.path_loop_events.append((self.steps, current_position, "Drone repeating a segment of its path.", "Adjust global or local planner to avoid redundant paths."))
                self.problems.append(f"Path loop detected at step {self.steps} at {current_position}.")
                break # Only report once per loop

    def detect_slowdowns(self, current_speed, speed_threshold=0.1, duration_threshold=5):
        if len(self.speed_history) < duration_threshold:
            return

        recent_speeds = list(self.speed_history)
        if all(s < speed_threshold for s in recent_speeds) and \
           (self.steps, current_speed) not in [(e[0], e[1]) for e in self.slowdown_events]:
            self.slowdown_events.append((self.steps, current_speed, f"Drone speed consistently below {speed_threshold} for {duration_threshold} steps.", "Investigate local obstacles or pathing issues."))
            self.problems.append(f"Slowdown detected at step {self.steps} with speed {current_speed}.")

    def report(self, drone_start, target_pos, local_planner_stuck_frames):
        report_content = []
        report_content.append("# NAVIGATION_REPORT.md\n")
        report_content.append("## Mission Efficiency\n")
        report_content.append(f"- **Total Steps**: {self.steps}\n")
        report_content.append(f"- **Total Distance Travelled**: {self.total_distance_travelled:.2f} units\n")
        report_content.append(f"- **Target Reach Time (steps)**: {self.calculate_target_reach_time()}\n")
        report_content.append(f"- **Return Home Time (steps)**: {self.calculate_return_home_time()}\n")
        report_content.append(f"- **Path Efficiency**: {self.calculate_path_efficiency(drone_start, target_pos):.2f}%\n")
        report_content.append(f"- **Average Speed**: {self.calculate_average_speed():.2f} units/step\n")
        report_content.append(f"- **Replans**: {self.replans}\n")
        report_content.append(f"- **Problems Detected**: {len(self.problems)}\n")

        report_content.append("\n## Detected Issues\n")

        if not self.stuck_events and not self.oscillation_events and \
           not self.orbiting_events and not self.path_loop_events and \
           not self.slowdown_events:
            report_content.append("- No significant navigation issues detected.\n")
        else:
            if self.stuck_events:
                report_content.append("### Stuck States\n")
                for i, (step, position) in enumerate(self.stuck_events):
                    report_content.append(f"#### Stuck Event {i+1}\n")
                    report_content.append(f"- **Cause**: Drone detected as stuck (minimal movement over {local_planner_stuck_frames} frames).\n")
                    report_content.append(f"- **Location**: {position} at step {step}\n")
                    report_content.append(f"- **Fix**: Automatic replanning initiated.\n")
            if self.oscillation_events:
                report_content.append("### Oscillation\n")
                for i, (step, position, cause, fix) in enumerate(self.oscillation_events):
                    report_content.append(f"#### Oscillation Event {i+1}\n")
                    report_content.append(f"- **Cause**: {cause}\n")
                    report_content.append(f"- **Location**: {position} at step {step}\n")
                    report_content.append(f"- **Fix**: {fix}\n")
            if self.orbiting_events:
                report_content.append("### Orbiting\n")
                for i, (step, position, cause, fix) in enumerate(self.orbiting_events):
                    report_content.append(f"#### Orbiting Event {i+1}\n")
                    report_content.append(f"- **Cause**: {cause}\n")
                    report_content.append(f"- **Location**: {position} at step {step}\n")
                    report_content.append(f"- **Fix**: {fix}\n")
            if self.path_loop_events:
                report_content.append("### Path Loops\n")
                for i, (step, position, cause, fix) in enumerate(self.path_loop_events):
                    report_content.append(f"#### Path Loop Event {i+1}\n")
                    report_content.append(f"- **Cause**: {cause}\n")
                    report_content.append(f"- **Location**: {position} at step {step}\n")
                    report_content.append(f"- **Fix**: {fix}\n")
            if self.slowdown_events:
                report_content.append("### Slowdowns\n")
                for i, (step, current_speed, cause, fix) in enumerate(self.slowdown_events):
                    report_content.append(f"#### Slowdown Event {i+1}\n")
                    report_content.append(f"- **Cause**: {cause}\n")
                    report_content.append(f"- **Location**: At step {step}, speed was {current_speed:.2f}\n")
                    report_content.append(f"- **Fix**: {fix}\n")

        with open("NAVIGATION_REPORT.md", "w") as f:
            f.writelines(report_content)

        # Also print a summary to console
        print("\n========== MISSION REPORT ==========")
        print(f"Steps: {self.steps}")
        print(f"Replans: {self.replans}")
        print(f"Obstacles Seen: {self.obstacles_seen}")
        print(f"Average Path Length: {self.average_path_length():.2f}")
        print(f"Total Distance Travelled: {self.total_distance_travelled:.2f}")
        print(f"Path Efficiency: {self.calculate_path_efficiency(drone_start, target_pos):.2f}%")
        print(f"Average Speed: {self.calculate_average_speed():.2f}")
        print(f"Target Reach Time: {self.calculate_target_reach_time()}")
        print(f"Return Home Time: {self.calculate_return_home_time()}")
        print(f"Problems Detected: {len(self.problems)}")
        print("====================================")