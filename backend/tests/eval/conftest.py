import pytest


def pytest_collection_modifyitems(config, items):
    if "slow" in config.getoption("markexpr"):
        return
    skip_slow = pytest.mark.skip(
        reason="loads the real embedding model; select it with -m slow"
    )
    for item in items:
        if item.get_closest_marker("slow"):
            item.add_marker(skip_slow)
