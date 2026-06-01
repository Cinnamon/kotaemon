class InvalidAttrDefinition(AttributeError):
    pass


class CyclicDependencyError(Exception):
    pass


class CyclicPipelineError(Exception):
    pass
