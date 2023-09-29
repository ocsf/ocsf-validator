import pytest

from ocsf_validator.types import *


def test_is_ocsf_type():
    assert is_ocsf_type(OcsfDictionary) is True
    assert is_ocsf_type(OcsfAttr) is True
    assert is_ocsf_type(str) is False
