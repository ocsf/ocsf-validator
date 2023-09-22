from dataclasses import dataclass, field
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
        "caption": NotRequired[str],
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
    path: str
    caption: str
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
    annotations: Dict[str, str]
    attributes: Dict[str, OcsfAttr]


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
