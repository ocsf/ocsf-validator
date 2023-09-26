"""Processors for directives like $include, extends, and profile.

"""


from typing import Any, Optional

from ocsf_validator.errors import (
    Collector,
    MissingBaseError,
    MissingIncludeError,
    MissingProfileError,
)
from ocsf_validator.reader import MatchMode, Reader
from ocsf_validator.types import OcsfAttr, OcsfDictionary, OcsfEvent, OcsfObject


def deep_merge(d1: dict[str, Any], *others: dict[str, Any], exclude: list[str] = []):
    """Recursive merging of dictionary keys.

    `d1 | d2 [| dn]` is more readable, but it doesn't merge recursively. If
    d1, d2, and d3 each have an "attributes" key with a dictionary value,
    only the first "attributes" dictionary will be present in the resulting
    dictionary. And thus this recursive merge."""
    for d in others:
        for k, v in d.items():
            if k in d1 and k not in exclude and isinstance(v, dict):
                deep_merge(d1[k], d[k])

            elif k not in d1:
                d1[k] = d[k]


def find_attrs(defn: type) -> str | None:
    """Find collections of OCSF Attributes in a TypedDict definition by type hint.

    The hope is that this will reduce the coupling between validation and the
    schema structure by making it possible to have attributes anywhere in
    the schema provided they're defined in `types.py`."""

    if hasattr(defn, "__annotations__"):
        for k, a in defn.__annotations__.items():
            if hasattr(a, "__args__"):
                target = a.__args__[-1]
                if target == OcsfAttr:
                    return k

    return None


def apply_include(
    reader: Reader,
    update: bool = True,
    recurse: bool = True,
    remove: bool = False,
    collector: Collector = Collector.default,
):
    """Process $include directives in a schema definition."""

    def include(defn: dict[str, Any], reader: Reader, key: str):
        """Perform the work of processing $include directives."""

        keys = list(defn.keys())
        for k in keys:
            if k == "$include":
                if isinstance(defn[k], str):
                    targets = [defn[k]]
                else:
                    targets = defn[k]

                for target in targets:
                    t = reader.find_include(target, key)
                    if t is None:
                        collector.handle(MissingIncludeError(key, target))
                    elif update:
                        deep_merge(defn, reader[t])

                if remove:
                    del defn[k]

            elif recurse and isinstance(defn[k], dict):
                include(defn[k], reader, key)

    def fn(reader: Reader, key: str):
        """A routing function to be called by Reader.apply() that preserves
        the processing options passed to includefn()."""
        include(reader[key], reader, key)

    reader.apply(fn, "objects/*", MatchMode.GLOB)
    reader.apply(fn, "events/*", MatchMode.GLOB)
    reader.apply(fn, "events/*/*", MatchMode.GLOB)


def apply_inheritance(
    reader: Reader, update: bool = True, collector: Collector = Collector.default
):
    """Process `extends` directives in schema definitions found in a Reader."""

    def extends(reader: Reader, key: str):
        """Process extends directives in a schema definition."""

        if "extends" in reader[key]:
            base = reader.find_base(reader[key]["extends"], key)
            if base is None:
                collector.handle(MissingBaseError(key, reader[key]["extends"]))
            elif update:
                deep_merge(reader[key], reader[base])

    reader.apply(extends, "objects/*", MatchMode.GLOB)
    reader.apply(extends, "events/*", MatchMode.GLOB)
    reader.apply(extends, "events/*/*", MatchMode.GLOB)


def apply_profiles(
    reader: Reader,
    white_list: Optional[list[str]] = None,
    update: bool = True,
    collector: Collector = Collector.default,
):
    """Process profiles directives in a schema definition by merging them into
    a given record type."""

    allowed = []
    if white_list is not None:
        for item in white_list:
            found = reader.find_include(item)
            if found is not None:
                allowed.append(found)

    def profiles(reader: Reader, key: str):
        if "profiles" in reader[key]:
            profiles = reader[key]["profiles"]
            if isinstance(profiles, str):
                profiles = [profiles]

            for profile in profiles:
                target = reader.find_profile(profile, key)
                if target is None:
                    collector.handle(MissingProfileError(key, profile))

                elif update and (white_list is None or target in allowed):
                    deep_merge(reader[key], reader[target])

    reader.apply(profiles, "objects/*", MatchMode.GLOB)
    reader.apply(profiles, "events/*", MatchMode.GLOB)
    reader.apply(profiles, "events/*/*", MatchMode.GLOB)


def apply_attributes(reader: Reader, collector: Collector = Collector.default):
    """Merge attribute details from the base dictionary.

    Attributes in OCSF are often only named in OCSF objects and events, with most
    properties of attributes being merged in from the base `dictionary.json`.

    This function looks for corresponding attribute keys first in the
    `dictionary.json` file for the object or event's extension, if applicable,
    and then looks to keys in the base `dictionary.json`."""

    def attributes(defn: type):
        attrs_key = find_attrs(defn)
        root_dict = {}
        dict_attrs_key = find_attrs(OcsfDictionary)

        if dict_attrs_key is not None:
            file = reader.find("dictionary.json")
            if file is not None:
                root_dict = file[dict_attrs_key]

        def merge_attrs(reader: Reader, key: str):
            if attrs_key is not None and dict_attrs_key is not None:
                extn = reader.extension(key)

                extn_dict = {}
                if extn is not None:
                    dict_path = reader.key("extensions", extn, "dictionary.json")
                    if dict_path in reader:
                        extn_dict = reader[dict_path][dict_attrs_key]

                for name, attr in reader[key][attrs_key].items():
                    if name in extn_dict:
                        deep_merge(reader[key][attrs_key][name], extn_dict[name])
                    if name in root_dict:
                        deep_merge(reader[key][attrs_key][name], root_dict[name])

        return merge_attrs

    reader.apply(attributes(OcsfObject), "objects/*", MatchMode.GLOB)
    reader.apply(attributes(OcsfEvent), "events/*", MatchMode.GLOB)
    reader.apply(attributes(OcsfEvent), "events/*/*", MatchMode.GLOB)
