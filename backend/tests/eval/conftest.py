import pytest


def pytest_collection_modifyitems(config, items):
    if "slow" in config.getoption("markexpr"):
        return
    skip_slow = pytest.mark.skip(
        reason="needs a real model or a real provider; deselected unless -m slow"
    )
    for item in items:
        if item.get_closest_marker("slow"):
            item.add_marker(skip_slow)
