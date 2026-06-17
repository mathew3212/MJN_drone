import time


class MemoryCell:

    def __init__(self):

        self.confidence = 0.0

        self.last_seen = 0.0

        self.occupancy = 0


class MemoryManager:

    def __init__(
        self,
        width,
        height,
        decay_rate=0.995,
        forget_threshold=0.05
    ):

        self.width = width
        self.height = height

        self.decay_rate = decay_rate
        self.forget_threshold = (
            forget_threshold
        )

        self._cells = [

            [

                MemoryCell()

                for _ in range(width)

            ]

            for _ in range(height)

        ]

    # =====================================
    # Grid Property (numpy array for consumers)
    # =====================================

    @property
    def grid(self):

        import numpy as np

        return np.array(
            [
                [
                    cell.confidence
                    for cell in row
                ]
                for row in self._cells
            ],
            dtype=float
        )

    # =====================================
    # Update Memory
    # =====================================

    def update(
        self,
        visible_obstacles
    ):

        current_time = time.time()

        # -------------------------
        # Decay Existing Memory
        # -------------------------

        for row in self._cells:

            for cell in row:

                cell.confidence *= (
                    self.decay_rate
                )

                if (

                    cell.confidence
                    <
                    self.forget_threshold

                ):

                    cell.confidence = 0.0

                    cell.occupancy = 0

        # -------------------------
        # Reinforce Observations
        # -------------------------

        for x, y in visible_obstacles:

            cell = self._cells[y][x]

            cell.confidence = min(
                1.0,
                cell.confidence + 0.25
            )

            cell.last_seen = (
                current_time
            )

            cell.occupancy = 1

    # =====================================
    # Query Confidence
    # =====================================

    def get_confidence(
        self,
        x,
        y
    ):

        return self._cells[y][x].confidence

    # =====================================
    # Query Last Seen
    # =====================================

    def get_last_seen(
        self,
        x,
        y
    ):

        return self._cells[y][x].last_seen

    # =====================================
    # Occupancy Query
    # =====================================

    def is_occupied(
        self,
        x,
        y
    ):

        return (

            self._cells[y][x]
            .occupancy
            == 1

        )

    # =====================================
    # Heatmap Export
    # =====================================

    def get_heatmap(self):

        heatmap = []

        for row in self._cells:

            heatmap.append(

                [

                    cell.confidence

                    for cell in row

                ]

            )

        return heatmap

    # =====================================
    # Statistics
    # =====================================

    def memory_density(self):

        remembered = 0

        total = (
            self.width
            * self.height
        )

        for row in self._cells:

            for cell in row:

                if (
                    cell.confidence > 0
                ):

                    remembered += 1

        return (
            remembered
            / total
        ) * 100

    # =====================================
    # Active Cell Count
    # =====================================

    def active_cells(self):

        count = 0

        for row in self._cells:

            for cell in row:

                if cell.confidence > 0:

                    count += 1

        return count