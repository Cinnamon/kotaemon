class KHException(Exception):
    pass


class HookNotDeclared(KHException):
    pass


class HookAlreadyDeclared(KHException):
    pass
