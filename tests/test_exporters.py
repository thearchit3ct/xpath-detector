import pytest

from xpath_detector.exporters.base import Exporter


def test_exporter_is_abstract():
    with pytest.raises(TypeError):
        Exporter()
