import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import pytest


@pytest.mark.parametrize(
    "name,path",
    [
        ("Aya Khan", "/api/jobs/workspace"),
        ("Sam Ali", "/api/staff/workspace"),
        ("Jules Lee", "/api/platform/workspace"),
    ],
)
def test_bounded_workspace_burst(sign_in, name, path):
    client, _, _ = sign_in(name)

    def request(_):
        start = time.perf_counter()
        response = client.get(path)
        assert response.status_code == 200
        return (time.perf_counter() - start) * 1000

    with ThreadPoolExecutor(max_workers=4) as pool:
        times = sorted(pool.map(request, range(16)))
    print(f"{path}: n=16 workers=4 median={statistics.median(times):.2f}ms p95={times[15]:.2f}ms")
