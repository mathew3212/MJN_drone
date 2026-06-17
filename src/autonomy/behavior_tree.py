class Node:

    def run(self):

        raise NotImplementedError


class Selector(Node):

    def __init__(self, children):

        self.children = children

    def run(self):

        for child in self.children:

            if child.run():

                return True

        return False


class Sequence(Node):

    def __init__(self, children):

        self.children = children

    def run(self):

        for child in self.children:

            if not child.run():

                return False

        return True


class Condition(Node):

    def __init__(self, fn):

        self.fn = fn

    def run(self):

        return self.fn()


class Action(Node):

    def __init__(self, fn):

        self.fn = fn

    def run(self):

        self.fn()

        return True