class MemoryEngine:

    def __init__(self):
        self.visited = set()

    def remember(self, position):
        self.visited.add(position)

    def has_visited(self, position):
        return position in self.visited