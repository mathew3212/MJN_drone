class BatteryManager:

    def __init__(
        self,
        capacity=100.0,
        reserve_level=20.0,
        critical_level=10.0
    ):

        self.capacity = capacity

        self.level = capacity

        self.reserve_level = reserve_level

        self.critical_level = critical_level

        self.consumption_rate = 0.05

        self.total_consumed = 0.0

    # ===================================
    # Consume Battery
    # ===================================

    def update(
        self,
        distance_travelled,
        obstacle_count
    ):

        drain = (

            distance_travelled
            * self.consumption_rate

        )

        drain += (

            obstacle_count
            * 0.002

        )

        self.level -= drain

        self.total_consumed += drain

        if self.level < 0:

            self.level = 0

    # ===================================
    # Status Checks
    # ===================================

    def is_low(self):

        return (

            self.level
            <= self.reserve_level

        )

    def is_critical(self):

        return (

            self.level
            <= self.critical_level

        )

    def is_empty(self):

        return self.level <= 0

    # ===================================
    # Remaining %
    # ===================================

    def percentage(self):

        return (

            self.level
            / self.capacity

        ) * 100

    # ===================================
    # Report
    # ===================================

    def report(self):

        print()

        print(
            "========== BATTERY =========="
        )

        print(
            f"Remaining: "
            f"{self.percentage():.2f}%"
        )

        print(
            f"Consumed: "
            f"{self.total_consumed:.2f}"
        )

        print(
            "============================="
        )