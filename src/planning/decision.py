class DecisionEngine:

    def choose_action(
        self,
        perception,
        world,
        drone,
        memory
    ):

        possible_moves = [
            (1, 0),   # right
            (-1, 0),  # left
            (0, 1),   # up
            (0, -1)   # down
        ]

        best_move = None
        best_score = float("-inf")

        target_x = drone.x + perception["target_dx"]
        target_y = drone.y + perception["target_dy"]

        for move in possible_moves:

            nx = drone.x + move[0]
            ny = drone.y + move[1]

            # Stay inside world
            if nx < 0 or nx >= world.width:
                continue

            if ny < 0 or ny >= world.height:
                continue

            # Avoid obstacles
            if world.is_obstacle(nx, ny):
                continue

            score = 0

            # Move closer to target
            distance_to_target = (
                abs(target_x - nx)
                + abs(target_y - ny)
            )

            score -= distance_to_target

            # Strong penalty for revisiting cells
            if memory.has_visited((nx, ny)):
                score -= 100

            if score > best_score:
                best_score = score
                best_move = move
            
            if world.is_obstacle(nx, ny):
                print(f"Obstacle detected at {(nx, ny)}")
                continue

        return best_move