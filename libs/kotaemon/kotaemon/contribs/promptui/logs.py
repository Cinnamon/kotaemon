class ResultLog:
    """Callback getter to get the desired log result

    The callback resolution will be as follow:
        1. Explicit string name
        2. Implicitly by: `get_<name>`
        3. Pass through
    """

    @staticmethod
    def _get_input(obj):
        return obj["input"]

    @staticmethod
    def _get_output(obj):
        return obj["output"]
