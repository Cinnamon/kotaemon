import yaml


class YAMLNoDateSafeLoader(yaml.SafeLoader):
    """Load datetime as strings, not dates"""

    @classmethod
    def remove_implicit_resolver(cls, tag_to_remove):
        """Remove implicit resolvers for a particular tag

        Args:
            tag_to_remove (str): YAML tag to remove
        """
        if "yaml_implicit_resolvers" not in cls.__dict__:
            cls.yaml_implicit_resolvers = cls.yaml_implicit_resolvers.copy()

        for first_letter, mappings in cls.yaml_implicit_resolvers.items():
            cls.yaml_implicit_resolvers[first_letter] = [
                (tag, regexp) for tag, regexp in mappings if tag != tag_to_remove
            ]


YAMLNoDateSafeLoader.remove_implicit_resolver("tag:yaml.org,2002:timestamp")
