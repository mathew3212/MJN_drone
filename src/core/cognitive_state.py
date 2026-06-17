import numpy as np


class CognitiveState:

    def __init__(
        self,
        width,
        height
    ):

        self.width = width
        self.height = height

        self.grid = np.zeros(
            (
                height,
                width
            ),
            dtype=float
        )

        # Weights

        self.perception_weight = 0.45
        self.memory_weight = 0.25
        self.context_weight = 0.30
        self.risk_weight = 0.40

    def update(
        self,
        perception_map,
        memory_map,
        context_map,
        risk_map=None,
    ):
        risk_grid = 0

        if risk_map is not None:
            risk_grid = risk_map.grid

        self.grid = (

            self.context_weight
            *
            context_map.grid

            -

            self.perception_weight
            *
            perception_map.grid

            -

            self.memory_weight
            *
            memory_map.grid

            -

            self.risk_weight
            *
            risk_grid

        )

        return self

    def get_score(
        self,
        x,
        y
    ):

        return self.grid[
            y,
            x
        ]
