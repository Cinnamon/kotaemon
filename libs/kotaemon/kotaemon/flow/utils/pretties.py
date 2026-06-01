import re


def reindent_docstring(docin: str) -> str:
    """Remove beginning whitespace in a docstring

    Happens when the docstring is indented in method, function, class... but we want to
    make it look nice in CLI.

    Args:
        docin: the docstring to reindent

    Returns:
        the reindented docstring
    """
    if not docin:
        return ""

    whitespaces = re.findall(r"\n[ \t]+", docin)
    if whitespaces:
        min_whitespace = min(whitespaces)[1:]
        lines = []
        for line in docin.splitlines():
            if line.startswith(min_whitespace):
                line = line[len(min_whitespace) :]
            lines.append(line)
        docin = "\n".join(lines).strip()
    return docin


def flatten_dict(indict: dict) -> dict:
    """Flatten nested dict into 1-level dict

    Example:
        >>> flatten_dict({"a": {"b": 1}, "c": 2})
        {"a.b": 1, "c": 2}

    Args:
        indict: input dict

    Returns:
        flattened dict
    """
    outdict = {}
    for key, value in indict.items():
        if isinstance(value, dict):
            for subkey, subvalue in flatten_dict(value).items():
                outdict[f"{key}.{subkey}"] = subvalue
        else:
            outdict[key] = value
    return outdict


def unflatten_dict(indict: dict) -> dict:
    """Unflatten 1-level dict into nested dict

    Example:
        >>> unflatten_dict({"a.b": 1, "c": 2})
        {"a": {"b": 1}, "c": 2}

    Args:
        indict: input dict

    Returns:
        unflattened dict
    """
    outdict: dict = {}
    for key, value in indict.items():
        key = key.strip(".")
        subkeys = key.split(".")
        subdict = outdict
        for subkey in subkeys[:-1]:
            if subkey not in subdict:
                subdict[subkey] = {}
            subdict = subdict[subkey]
        subdict[subkeys[-1]] = value
    return outdict
