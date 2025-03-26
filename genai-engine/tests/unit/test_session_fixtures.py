import pytest
from schemas.enums import RuleScope
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.clients.unit_test_client import get_genai_engine_test_client

client: GenaiEngineTestClientBase = None


# If we set this client at the global level, pytest will initialize a client for every module.
# As part of the initialization, we delete / create api keys. If all clients are created sequentially,
# will cause the key deactivations of the next to overwrite the key creation of the previous. Use a module
# scoped fixture to initialize a new client for each module, after the tests of the previous module have run
@pytest.fixture(scope="session", autouse=True)
def initialize_client():
    global client
    client = get_genai_engine_test_client()
    return client


# These are really only relevant for integration tests to clear old data.
@pytest.fixture(scope="session", autouse=True)
def clear_old_tasks_before_test_run(initialize_client):
    status_code, tasks = client.search_tasks(page_size=250)
    tasks = tasks.tasks
    assert status_code == 200
    for task in tasks:
        status_code = client.delete_task(task.id)
        assert status_code == 204
    yield


# @pytest.fixture(scope="session", autouse=True)
# def query_all_inferences_after_tests():
#     yield
#     # Global client will have deactivated keys after all tests have run, so refresh with a new one
#     client = get_genai_engine_test_client()
#     all_inferences = client.query_all_inferences()
#     # Make sure all historical data is still parseable / no issues with old inferences
#     assert isinstance(all_inferences, QueryInferencesResponse)


@pytest.fixture(scope="session", autouse=True)
def clear_default_rules_before_test_run(initialize_client):
    status_code, rules = client.search_rules(
        rule_scopes=[RuleScope.DEFAULT],
        page_size=250,
    )
    rules = rules.rules
    assert status_code == 200
    for rule in rules:
        status_code = client.delete_default_rule(rule.id)
        assert status_code == 200
    yield


@pytest.mark.unit_tests
def test_run_session_fixtures():
    # Dummy test to trigger the fixtures in this module to run. Fixtures will not run if there are no tests in the module.
    pass
