class Generator:
    """A generator that stores return value from another generator"""

    def __init__(self, gen):
        self.gen = gen

    def __iter__(self):
        self.value = yield from self.gen
        return self.value
