# pytest configuration fixtures
import os
import pytest


@pytest.fixture(autouse=True, scope="session")
def _set_helen_api_key_env():
    """Set a dummy HELEN_API_KEY for the test session.

    Many tests invoke `helen <file>` via subprocess. The CLI performs a
    preflight config check (`_preflight_config_check`) that exits with
    "Helen is not configured" if no API key is available. CI has no
    ~/.helen/config.yaml, so without this fixture every subprocess run
    fails before the interpreter even starts.

    A dummy value is enough — the config check only verifies the key is
    non-empty; these tests run pure language programs that never touch
    the LLM.

    Tests that specifically test yaml loading should patch out this env
    var locally (see test_load_config_from_yaml for an example).
    """
    if not os.environ.get("HELEN_API_KEY"):
        os.environ["HELEN_API_KEY"] = "test-dummy-key-for-ci"
