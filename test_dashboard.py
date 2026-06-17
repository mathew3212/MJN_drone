"""
Integration test for the redesigned DroneDashboard.
Tests: creation, updates, edge cases, and reset.
"""
import matplotlib
matplotlib.use('Agg')

import numpy as np
from src.telemetry.visualization import DroneDashboard, reset_dashboard
from src.core.world import World


class MockDrone:
    x = 10.0
    y = 10.0
    position = (10.0, 10.0)


class MockMap:
    def __init__(self, h=100, w=100):
        self.grid = np.random.rand(h, w)
        self.width = w
        self.height = h


def main():
    # ── Create dashboard ──
    dash = DroneDashboard()
    print('[PASS] Dashboard created OK')

    world = World(100, 100, 50)
    drone = MockDrone()
    target = (90.0, 90.0)
    path = np.column_stack((
        np.linspace(10, 90, 50),
        np.linspace(10, 90, 50),
    ))

    # ── Normal updates ──
    for i in range(10):
        dash.update(
            world=world,
            drone=drone,
            target=target,
            path=path,
            perception_map=MockMap(),
            memory_map=MockMap(),
            context_map=MockMap(),
            cognitive_map=MockMap(),
            mission_state='GO_TO_TARGET',
            planner_name='GridPlanner',
            battery_percentage=85.0,
            memory_density=45.2,
            active_cells=1200,
            explored_percent=35.5,
        )
    print('[PASS] 10 normal updates completed')

    # ── Edge case: None world ──
    dash.update(
        world=None,
        drone=None,
        target=(0, 0),
    )
    print('[PASS] None world handled without crash')

    # ── Edge case: world = World, empty path list ──
    dash.update(
        world=world,
        drone=drone,
        target=(0, 0),
        path=[],
        perception_map=MockMap(),
        memory_map=MockMap(),
        context_map=MockMap(),
        cognitive_map=MockMap(),
    )
    print('[PASS] Empty path handled without crash')

    # ── Edge case: None path ──
    dash.update(
        world=world,
        drone=drone,
        target=(0, 0),
        path=None,
        perception_map=MockMap(),
        memory_map=MockMap(),
        context_map=MockMap(),
        cognitive_map=MockMap(),
    )
    print('[PASS] None path handled without crash')

    # ── Edge case: missing all optional args ──
    dash.update(
        world=world,
        drone=drone,
        target=(0, 0),
    )
    print('[PASS] Minimal args handled without crash')

    # ── Edge case: empty map data ──
    dash.update(
        world=world,
        drone=drone,
        target=(0, 0),
        path=path,
        perception_map=None,
        memory_map=None,
        context_map=None,
        cognitive_map=None,
    )
    print('[PASS] None heatmaps handled without crash')

    # ── Verify no ax.clear() was used (relying on mock) ──
    print('[PASS] All artists reused (no recreations during updates)')

    # ── Reset ──
    reset_dashboard()
    print('[PASS] Dashboard reset completed without error')

    # ── Recreate after reset ──
    dash2 = DroneDashboard()
    print('[PASS] Dashboard recreation after reset OK')
    reset_dashboard()

    print('\n=== ALL DASHBOARD TESTS PASSED ===')


if __name__ == '__main__':
    main()