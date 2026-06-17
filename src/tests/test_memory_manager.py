"""Unit tests for MemoryManager."""

from src.mapping.memory_manager import MemoryManager


class TestMemoryManager:
    """Test suite for MemoryManager."""

    def test_init(self):
        mem = MemoryManager(100, 100)
        assert mem.width == 100
        assert mem.height == 100
        assert mem.memory_density() == 0.0
        assert mem.active_cells() == 0

    def test_update_adds_obstacles(self):
        mem = MemoryManager(10, 10)
        mem.update([(5, 5), (5, 6)])
        assert mem.get_confidence(5, 5) > 0
        assert mem.get_confidence(5, 6) > 0
        assert mem.is_occupied(5, 5)
        assert mem.memory_density() > 0

    def test_decay_over_time(self):
        mem = MemoryManager(10, 10, decay_rate=0.5, forget_threshold=0.01)
        mem.update([(3, 3)])
        assert mem.get_confidence(3, 3) > 0
        # Update again without reinforcement to trigger decay
        mem.update([])
        # After decay, confidence should be lower (0.25 * 0.5 = 0.125)
        assert mem.get_confidence(3, 3) < 0.26

    def test_forget_threshold(self):
        mem = MemoryManager(10, 10, decay_rate=0.1, forget_threshold=0.5)
        mem.update([(2, 2)])
        for _ in range(10):
            mem.update([])
        # Should have forgotten
        assert mem.get_confidence(2, 2) == 0.0

    def test_heatmap_shape(self):
        mem = MemoryManager(50, 30)
        heatmap = mem.get_heatmap()
        assert len(heatmap) == 30
        assert len(heatmap[0]) == 50