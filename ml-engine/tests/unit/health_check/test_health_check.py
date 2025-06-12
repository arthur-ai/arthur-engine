import time

import requests
from health_check import MLEngineHealthCheck


def test_health_check():
    address = "http://localhost:4444/health"
    health_check = MLEngineHealthCheck(check_in_seconds=1, port=4444)
    # start the check, it should pass right away
    health_check.start_server()
    # it may take a bit to start up, so wait for the first pass up to 5 seconds
    for i in range(50):
        try:
            requests.get(address)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.1)
    else:
        # server didn't start in the time limit
        assert False

    assert requests.get(address).status_code == 200

    # wait 2 seconds, it should report fail
    time.sleep(2)
    assert requests.get(address).status_code == 500

    # ping the health check and it should be healthy again for a second
    health_check.liveness_ping()
    assert requests.get(address).status_code == 200

    # wait 2 more seconds so it starts failing again
    time.sleep(2)
    assert requests.get(address).status_code == 500
