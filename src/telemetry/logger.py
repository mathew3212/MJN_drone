import csv


class MissionLogger:

    def __init__(self):

        self.filename = (
            "mission_log.csv"
        )

        with open(
            self.filename,
            "w",
            newline=""
        ) as file:

            writer = csv.writer(
                file
            )

            writer.writerow(
                [
                    "step",
                    "x",
                    "y",
                    "path_length",
                    "visible_obstacles",
                    "coverage"
                ]
            )

    def log(
        self,
        step,
        x,
        y,
        path_length,
        visible_obstacles,
        coverage
    ):

        with open(
            self.filename,
            "a",
            newline=""
        ) as file:

            writer = csv.writer(
                file
            )

            writer.writerow(
                [
                    step,
                    x,
                    y,
                    path_length,
                    visible_obstacles,
                    coverage
                ]
            )