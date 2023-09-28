from pathlib import Path
from typing import Any, Callable, Optional

from ocsf_validator.errors import (Collector, IncludeTypeMismatchError,
                                   MissingBaseError, MissingIncludeError,
                                   MissingProfileError,
                                   RedundantProfileIncludeError,
                                   SelfInheritanceError, UndetectableTypeError)
from ocsf_validator.reader import Reader
from ocsf_validator.type_mapping import TypeMapping
from ocsf_validator.types import (ATTRIBUTES_KEY, EXTENDS_KEY, INCLUDE_KEY,
                                  PROFILES_KEY, OcsfDictionary, OcsfEvent,
                                  OcsfObject)


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


def exclude_props(t1: type, t2: type):
    if not hasattr(t1, "__annotations__") or not hasattr(t2, "__annotations__"):
        raise Exception("Unexpected types in comparison")
    s1 = set(t1.__annotations__.keys())
    s2 = set(t2.__annotations__.keys())
    return s2 - s1


class DependencyResolver:
    def __init__(self, reader: Reader, types: TypeMapping):
        self._reader = reader
        self._types = types

    def resolve_include(
        self, target: str, relative_to: Optional[str] = None
    ) -> str | None:
        """Find a file from an OCSF $include directive.

        For a given file f, search:
          extn/f
          extn/f.json
          f
          f.json
        """

        filenames = [target]
        if Path(target).suffix != ".json":
            filenames.append(target + ".json")

        for file in filenames:
            if relative_to is not None:
                # Search extension for relative include path, e.g. /includes/thing.json -> /extensions/stuff/includes/thing.json
                extn = self._types.extension(relative_to)
                if extn is not None:
                    k = self._reader.key("extensions", extn, file)
                    if k in self._reader:
                        return k

            k = self._reader.key(file)
            if k in self._reader:
                return k

        return None

    def resolve_profile(self, profile: str, relative_to: str) -> str | None:
        """Find a file from an OCSF profiles directive.

        For a requested profile p, search:
          extn/profiles/p
          extn/profiles/p.json
          profiles/p
          profiles/p.json
          extn/p
          extn/p.json
          p
          p.json
        """
        file = self.resolve_include(profile, relative_to)
        if file is None:
            path = str(Path("profiles") / Path(profile))
            file = self.resolve_include(path, relative_to)

        return file

    def resolve_base(self, base: str, relative_to: str) -> str | None:
        """Find the location of a base record in an extends directive.

        For a requested base b in path events/activity/thin.json, search:
          events/activity/b.json
          events/b.json
          b.json       # this should be ignored but isn't yet

        For a requested base b in path extn/stuff/events/activity/thing.json, search:
          extn/stuff/events/activity/b.json
          events/activity/b.json
          extn/stuff/events/b.json
          events/b.json
          extn/stuff/b.json
          b.json       # these last two should be ignored but aren't yet
          extn/b.json  #

        parameters:
            base: str         The base as it's described in the extends
                              directive, without a path or an extension.
            relative_to: str  The full path from the schema root to the record
                              extending the base.
        """
        base_path = Path(base)
        if base_path.suffix != ".json":
            base += ".json"

        # Search the current directory and each parent directory
        path = Path(relative_to)
        extn = self._types.extension(relative_to)

        while path != path.parent:
            test = str(path / base)
            if test in self._reader and test != relative_to:
                return test
            elif extn is not None:
                woextn = Path(*list(path.parts)[2:]) / base
                test = str(woextn)
                if test in self._reader:
                    return test

            path = path.parent

        return None


class MergeParser:
    def __init__(
        self,
        reader: Reader,
        resolver: DependencyResolver,
        collector: Collector,
        types: TypeMapping,
    ):
        self._reader = reader
        self._resolver = resolver
        self._collector = collector
        self._types = types

    def applies_to(self, t: type) -> bool:
        return False

    def found_in(self, path: str) -> bool:
        return False

    def extract_targets(self, path: str) -> list[str]:
        return []

    def apply(self, path: str) -> None:
        for target in self.extract_targets(path):
            exclude = exclude_props(self._types[path], self._types[target])
            deep_merge(self._reader[path], self._reader[target], exclude=exclude)


class ExtendsParser(MergeParser):
    def applies_to(self, t: type) -> bool:
        return EXTENDS_KEY in t.__required_keys__ or EXTENDS_KEY in t.__optional_keys__

    def found_in(self, path: str) -> bool:
        return EXTENDS_KEY in self._reader[path]

    def extract_targets(self, path: str) -> list[str]:
        target = self._reader[path][EXTENDS_KEY]
        base = self._resolver.resolve_base(target, path)
        if base is None:
            self._collector.handle(MissingBaseError(path, target))
            return []
        else:
            if self._types[base] not in [OcsfEvent, OcsfObject]:
                self._collector.handle(
                    InvalidTypeMismatchError(
                        path, base, "OcsfObject | OcsfEvent", "extends"
                    )
                )
            return [self._resolver.resolve_base(target, path)]


class ProfilesParser(MergeParser):
    def applies_to(self, t: type) -> bool:
        return (
            PROFILES_KEY in t.__required_keys__ or PROFILES_KEY in t.__optional_keys__
        )

    def found_in(self, path: str) -> bool:
        return PROFILES_KEY in self._reader[path]

    def extract_targets(self, path: str) -> list[str]:
        targets = []
        profiles = self._reader[path][PROFILES_KEY]

        if isinstance(profiles, str):
            profiles = [profiles]

        for profile in profiles:
            target = self._resolver.resolve_profile(profile, path)
            if target is None:
                self._collector.handle(MissingProfileError(path, profile))
            else:
                targets.append(target)

        return targets


class AttributesParser(MergeParser):
    def applies_to(self, t: type) -> bool:
        return (
            ATTRIBUTES_KEY in t.__required_keys__
            or ATTRIBUTES_KEY in t.__optional_keys__
        )

    def found_in(self, path: str) -> bool:
        return ATTRIBUTES_KEY in self._reader[path]

    def extract_targets(self, path: str) -> list[str]:
        if self._types[path] == OcsfDictionary:
            return []
        else:
            return [self._reader.key("dictionary.json")]
            # TODO the above should include extension dictionaries for correctness

    def _extn_dict(self, path):
        extn = self._types.extension(path)
        if extn is not None:
            dict_path = self._reader.key("extensions", extn, "dictionary.json")
            if dict_path in self._reader:
                return self._reader[dict_path][ATTRIBUTES_KEY]
        return {}

    def _root_dict(self):
        file = self._reader.find("dictionary.json")
        if file is not None:
            return file[ATTRIBUTES_KEY]
        return {}

    def apply(self, path: str):
        attrs = self._reader[path][ATTRIBUTES_KEY]
        root = self._root_dict()
        extn = self._extn_dict(path)

        # TODO is the dict name comparison enough or do we need to find by the `name` key?
        for name, attr in attrs.items():
            if name in extn:
                deep_merge(attrs[name], extn[name])
            if name in root:
                deep_merge(attrs[name], root[name])


class IncludeParser(MergeParser):
    def applies_to(self, t: type) -> bool:
        return INCLUDE_KEY in t.__required_keys__ or INCLUDE_KEY in t.__optional_keys__

    def applies_to(self, t: type) -> bool:
        return "__required_keys__" in t.__dict__ and (
            INCLUDE_KEY in t.__optional_keys__ or INCLUDE_KEY in t.__required_keys__
        )

    def _has_includes(self, defn: dict[str, Any]) -> bool:
        """Recursively search for $include directives."""
        keys = list(defn.keys())
        for k in keys:
            if k == INCLUDE_KEY:
                return True
            elif isinstance(defn[k], dict):
                if self._has_includes(defn[k]):
                    return True
        return False

    def found_in(self, path: str) -> bool:
        return self._has_includes(self._reader[path])

    def _parse_includes(
            self, defn: dict[str, Any], path: str, trail: list[str] = [], update: bool = True, remove: bool = False
    ) -> list[str]:
        """Find $include directives, optionally apply them, optionally
        remove the $include directive, and return a list of include targets.
        """
        keys = list(defn.keys())
        found = []

        for k in keys:
            if k == INCLUDE_KEY:
                if isinstance(defn[k], str):
                    targets = [defn[k]]
                else:
                    targets = defn[k]

                for target in targets:
                    t = self._resolver.resolve_include(target, path)
                    found.append(t)
                    if t is None:
                        self._collector.handle(MissingIncludeError(path, target))
                    elif update:
                        other = self._reader[t]
                        for key in trail:
                            other = other[key]
                        deep_merge(defn, other)

                if remove:
                    del defn[k]

            elif isinstance(defn[k], dict):
                found += self._parse_includes(defn[k], path, trail + [k], update, remove)

        return found

    def extract_targets(self, path: str) -> list[str]:
        return self._parse_includes(
            self._reader[path], path, update=False, remove=False
        )

    def apply(self, path: str) -> None:
        self._parse_includes(self._reader[path], path, update=True, remove=False)


class Dependencies:
    def __init__(self):
        self._dependencies: dict[str, list[tuple[str, str]]] = {}

    def add(self, child: str, parent: str, label: str = ""):
        if child not in self._dependencies:
            self._dependencies[child] = []
        self._dependencies[child].append([parent, label])

    def __iter__(self):
        return iter(self._dependencies)

    def __getitem__(self, key: str) -> list[str]:
        return self._dependencies[key]

    def keys(self):
        return self._dependencies.keys()

    def exists(self, path: str, target: str, directive: Optional[str] = None):
        if path in self._dependencies:
            for item in self._dependencies[path]:
                if item[0] == target:
                    if directive is not None:
                        if directive == item[1]:
                            return True
                    else:
                        return True
        return False


def process_includes(
    reader: Reader,
    collector: Collector = Collector.default,
    types: Optional[TypeMapping] = None,
    update: bool = True,
):
    if types is None:
        types = TypeMapping(reader, collector)

    resolver = DependencyResolver(reader, types)

    parsers = {
        EXTENDS_KEY: ExtendsParser(reader, resolver, collector, types),
        PROFILES_KEY: ProfilesParser(reader, resolver, collector, types),
        INCLUDE_KEY: IncludeParser(reader, resolver, collector, types),
        ATTRIBUTES_KEY: AttributesParser(reader, resolver, collector, types),
    }
    fulfilled: set[str] = set()
    dependencies = Dependencies()

    for path in reader.match():
        for directive, parser in parsers.items():
            if parser.found_in(path):
                for target in parser.extract_targets(path):
                    dependencies.add(path, target, directive)

    def process(path: str):
        if path not in fulfilled:
            if path in dependencies:
                for dependency, directive in dependencies[path]:
                    if dependency == path:
                        collector.handle(SelfInheritanceError(path, target))
                    elif directive == INCLUDE_KEY and dependencies.exists(
                        path, dependency, PROFILES_KEY
                    ):
                        collector.handle(RedundantProfileIncludeError(path, dependency))
                    else:
                        process(dependency)

            if update:
                for directive, parser in parsers.items():
                    if parser.found_in(path):
                        parser.apply(path)

            fulfilled.add(path)

    for path in dependencies.keys():
        #print(path, dependencies[path])
        process(path)


