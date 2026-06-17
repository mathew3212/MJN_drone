"""Unit tests for path planners."""

import numpy as np

from src.mapping.occupancy_grid import OccupancyGrid
from src.planning.grid_planner import GridPlanner
from src.planning.dstar_lite import DStarLite
from src.mapping.cost_map import CostMap


class TestGridPlanner:
    """Test the GridPlanner pathfinding."""

    def test_simple_path(self):
        grid = OccupancyGrid(10, 10)
        planner = GridPlanner(grid)
        path = planner.find_path((0, 0), (5, 5))
        assert path is not None
        assert len(path) > 0
        assert path[0] == (0, 0)
        assert path[-1] == (5, 5)

    def test_path_avoids_blocked_cell(self):
        grid = OccupancyGrid(5, 5)
        # Block a single cell that is not on the direct line
        grid.mark_obstacle(2, 2)
        planner = GridPlanner(grid)
        path = planner.find_path((0, 0), (4, 4))
        assert path is not None
        # Should find a path around the obstacle

    def test_blocked_goal(self):
        grid = OccupancyGrid(5, 5)
        grid.mark_obstacle(4, 4)
        planner = GridPlanner(grid)
        path = planner.find_path((0, 0), (4, 4))
        assert path is None

    def test_dstar_lite_path(self):
        grid = OccupancyGrid(10, 10)
        planner = DStarLite(grid)
        path = planner.find_path((0, 0), (5, 5))
        assert path is not None
        assert path[0] == (0, 0)
        assert path[-1] == (5, 5)

    def test_grid_planner_with_cost_map(self):
        grid = OccupancyGrid(10, 10)
        cost_map = CostMap(10, 10)
        planner = GridPlanner(grid, cost_map=cost_map)
        path = planner.find_path((0, 0), (5, 5))
        assert path is not None
        assert path[-1] == (5, 5)


class TestCostMap:
    """Test the CostMap integration."""

    def test_update(self):
        class MockMap:
            def __init__(self, h=10, w=10):
                self.grid = np.ones((h, w), dtype=float)
                self.width = w
                self.height = h

        cost_map = CostMap(10, 10)
        result = cost_map.update(
            perception_map=MockMap(),
            memory_map=MockMap(),
            context_map=MockMap(),
            risk_map=MockMap(),
            trajectory_map=MockMap(),
        )
        assert result is cost_map
        assert cost_map.grid.shape == (10, 10)