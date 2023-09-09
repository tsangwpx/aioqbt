import pytest

from aioqbt.exc import VersionError
from aioqbt.version import (
    APIVersion,
    ClientVersion,
    param_version_check,
    version_check,
    version_satisfy,
)


def test_client_version():
    string = "4.2.5.1"
    version = ClientVersion.parse(string)

    assert version.major == 4
    assert version.minor == 2
    assert version.patch == 5
    assert version.build == 1
    assert version.status == ""

    assert version == version
    assert str(version) == string
    assert version != object()
    assert {version: version}[version] == version

    with pytest.raises(TypeError):
        assert version < object()

    string2 = "4.2.5rc1"
    version2 = ClientVersion.parse(string2)
    assert version2.status == "rc1"
    assert str(version2) == "4.2.5rc1"
    assert version2 < version

    with pytest.raises(ValueError):
        ClientVersion.parse("4.2.x")

    with pytest.raises(ValueError):
        ClientVersion.parse("4.2.5bad")

    with pytest.raises(ValueError):
        ClientVersion(4, 2, 5, 0, "bad")


def test_api_version():
    version = APIVersion.parse("2.2.0")
    assert str(version) == "2.2.0"

    version2 = APIVersion.parse("2.2.5")
    assert version < version2

    with pytest.raises(ValueError):
        APIVersion.parse("2.2.5beta1")


def test_api_version_compare():
    a = APIVersion(4, 5, 1)

    assert APIVersion.compare(None, None) == 0
    assert APIVersion.compare(a, a) == 0
    assert APIVersion.compare(None, a) > 0
    assert APIVersion.compare(a, None) < 0

    b = APIVersion(4, 6, 1)
    assert APIVersion.compare(a, b) < 0
    assert APIVersion.compare(b, a) > 0


def test_version_utilities():
    v1 = APIVersion.parse("2.2.0")

    assert version_satisfy(v1, v1)
    assert version_satisfy(None, v1)

    v2 = APIVersion.parse("2.4.0")
    assert not version_satisfy(v1, v2)
    assert version_satisfy(v2, v1)

    with pytest.raises(VersionError):
        version_check(v1, v2)

    param_version_check("my_param", v1, v1)
    param_version_check("my_param", v2, v1)

    with pytest.raises(VersionError):
        param_version_check("param", v1, v2)


def test_param_version_check():
    v = APIVersion.parse("2.2.5")

    with pytest.raises(VersionError, match="parameter"):
        param_version_check("parameter", v, (2, 4, 5))
