from typing import (
    Any,
    Dict,
    NotRequired,
    Optional,
    Required,
    Sequence,
    TypedDict,
    TypeVar,
    Union,
)

ATTRIBUTES_KEY = "attributes"
PROFILES_KEY = "profiles"
EXTENDS_KEY = "extends"
INCLUDE_KEY = "$include"
OBSERVABLE_KEY = "observable"
OBSERVABLES_KEY = "observables"
TYPES_KEY = "types"


class OcsfVersion(TypedDict):
    version: str


class OcsfEnumMember(TypedDict):
    caption: str
    description: NotRequired[str]
    notes: NotRequired[str]


class OcsfEnum(TypedDict):
    enum: Dict[str, OcsfEnumMember]


class OcsfDeprecationInfo(TypedDict):
    message: Required[str]
    since: Required[str]


OcsfAttr = TypedDict(
    "OcsfAttr",
    {
        "$include": NotRequired[str],
        # "caption": NotRequired[str],
        "caption": str,
        "default": NotRequired[Any],
        "description": NotRequired[str],
        "enum": NotRequired[Dict[str, OcsfEnumMember]],
        "group": NotRequired[str],
        "is_array": NotRequired[bool],
        "max_len": NotRequired[int],
        "name": NotRequired[str],
        "notes": NotRequired[str],
        "observable": NotRequired[int],
        "range": NotRequired[Sequence[int]],
        "regex": NotRequired[str],
        "requirement": NotRequired[str],
        "sibling": NotRequired[str],
        "type": NotRequired[str],
        "type_name": NotRequired[str],
        "profile": NotRequired[Optional[Sequence[str]]],
        "values": NotRequired[Sequence[Any]],
        "@deprecated": NotRequired[OcsfDeprecationInfo],
    },
)


class OcsfExtension(TypedDict):
    uid: int
    name: str
    caption: str
    path: NotRequired[str]
    version: NotRequired[str]
    description: NotRequired[str]


class OcsfDictionaryTypes(TypedDict):
    attributes: Dict[str, OcsfAttr]
    caption: str
    description: str


class OcsfDictionary(TypedDict):
    attributes: Dict[str, OcsfAttr]
    caption: str
    description: str
    name: str
    types: NotRequired[OcsfDictionaryTypes]


class OcsfCategory(TypedDict):
    caption: str
    description: str
    uid: int
    type: NotRequired[str]  # older categories.json definitions


class OcsfCategories(TypedDict):
    attributes: Dict[str, OcsfCategory]
    caption: str
    description: str
    name: str


class OcsfInclude(TypedDict):
    caption: str
    attributes: Dict[str, OcsfAttr]
    description: NotRequired[str]
    annotations: NotRequired[Dict[str, str]]


class OcsfProfile(TypedDict):
    caption: str
    caption: str
    description: str
    meta: str
    name: str
    attributes: Dict[str, OcsfAttr]
    annotations: NotRequired[Dict[str, str]]


OcsfObject = TypedDict(
    "OcsfObject",
    {
        "caption": str,
        "description": str,
        "name": str,
        "attributes": Dict[str, OcsfAttr],
        "extends": NotRequired[Union[str, list[Optional[str]]]],
        "observable": NotRequired[int],
        "profiles": NotRequired[Sequence[str]],
        "constraints": NotRequired[Dict[str, Sequence[str]]],
        "$include": NotRequired[Union[str, Sequence[str]]],
        "@deprecated": NotRequired[OcsfDeprecationInfo],
    },
)


OcsfEvent = TypedDict(
    "OcsfEvent",
    {
        "attributes": Dict[str, OcsfAttr],
        "caption": str,
        "name": str,
        "uid": NotRequired[int],
        "category": NotRequired[str],
        "description": NotRequired[str],
        "extends": NotRequired[Union[str, list[Optional[str]]]],
        "profiles": NotRequired[Sequence[str]],
        "associations": NotRequired[Dict[str, Sequence[str]]],
        "constraints": NotRequired[Dict[str, Sequence[str]]],
        "observables": NotRequired[Dict[str, int]],
        "$include": NotRequired[Union[str, Sequence[str]]],
        "@deprecated": NotRequired[OcsfDeprecationInfo],
    },
)

T = TypeVar("T")
PerExt = Dict[Optional[str], T]
# Includable = Union[OcsfInclude, OcsfEnum, OcsfProfile]


class OcsfSchema(TypedDict):
    categories: PerExt[OcsfCategories]
    dictionaries: PerExt[OcsfDictionary]
    observables: Dict[int, OcsfObject | OcsfAttr]
    objects: PerExt[Dict[str, OcsfObject]]
    events: PerExt[Dict[str, OcsfEvent]]
    includes: PerExt[Dict[str, OcsfInclude]]
    profiles: PerExt[Dict[str, OcsfProfile]]
    enums: PerExt[Dict[str, OcsfEnum]]


def is_ocsf_type(t: type):
    return (
        t is OcsfEnumMember
        or t is OcsfEnum
        or t is OcsfDeprecationInfo
        or t is OcsfAttr
        or t is OcsfExtension
        or t is OcsfDictionaryTypes
        or t is OcsfDictionary
        or t is OcsfCategory
        or t is OcsfCategories
        or t is OcsfInclude
        or t is OcsfProfile
        or t is OcsfObject
        or t is OcsfEvent
    )


def leaf_type(defn: type, prop: str) -> type | None:
    if hasattr(defn, "__annotations__") and prop in defn.__annotations__:
        t = defn.__annotations__[prop]
        if hasattr(t, "__args__"):
            return t.__args__[-1]
        else:
            return t
    return None
