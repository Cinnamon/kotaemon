import pluggy

hookspec = pluggy.HookspecMarker("ktem")
hookimpl = pluggy.HookimplMarker("ktem")


@hookspec
def ktem_declare_extensions() -> dict:  # type: ignore
    """Called before the run() function is executed.

    This hook is called without any arguments, and should return a dictionary.
    The dictionary has the following structure:

        ```
        {
            "id": str,      # cannot contain . or /
            "name": str,    # human-friendly name of the plugin
            "version": str,
            "support_host": str,
            "functionality": {
                "reasoning": {
                    id: {                         # cannot contain . or /
                        "name": str,
                        "callbacks": {},
                        "settings": {},
                    },
                },
                "index": {
                    "name": str,
                    "callbacks": {
                        "get_index_pipeline": callable,
                        "get_retrievers": {name: callable}
                    },
                    "settings": {},
                },
            },
        }
        ```
    """
