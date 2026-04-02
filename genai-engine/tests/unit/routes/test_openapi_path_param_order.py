"""
Guard against FastAPI silently reordering path parameters in the OpenAPI spec.

Background
----------
FastAPI places Depends()-based path params *after* all inline Path() params in
the generated spec, regardless of function signature order.  When a route mixes
inline Path() params (e.g. prompt_version) with Depends()-based decoded params
(e.g. prompt_name via Depends(decoded_prompt_name)), the spec ends up listing
prompt_version first — which is the wrong URL order.  The generated api-client.ts
follows that spec order, silently swapping parameter positions.  Because all the
params share type `string`, TypeScript cannot catch the mismatch.

The fix is to declare every decoded path param as
    Annotated[str, Path(), AfterValidator(decode_path_param)]
so all path params are inline and FastAPI respects the function signature order.

Known exception
---------------
task_id is always resolved via Depends(get_validated_task), so FastAPI consistently
places it *last* in every route's spec parameter list regardless of its position in
the URL template.  All generated client call sites are written to match this
established ordering, so it is excluded from this check.

What this test guards
---------------------
For every route, the non-task_id path parameters must appear in the spec in the
same relative order as they do in the URL path template.  A violation means a new
Depends()-based param was introduced for a path param that is not task_id, which
will reorder it in the spec and silently break the generated API client.
"""

import re

import pytest

# task_id is consistently extracted via Depends(get_validated_task) and always
# lands last in the spec.  All call sites already account for this, so we
# exclude it from the ordering assertion.
_EXCLUDED_PARAMS = {"task_id"}


@pytest.mark.unit_tests
def test_openapi_path_params_order_matches_url_template():
    """Non-task_id path params must appear in spec in the same order as the URL."""
    from server import get_app_with_routes

    app = get_app_with_routes()
    schema = app.openapi()

    violations = []

    for path_template, path_item in schema.get("paths", {}).items():
        # URL template order, excluding known exceptions
        url_param_order = [
            p
            for p in re.findall(r"\{(\w+)\}", path_template)
            if p not in _EXCLUDED_PARAMS
        ]

        for method, operation in path_item.items():
            if method not in ("get", "post", "put", "delete", "patch"):
                continue

            parameters = operation.get("parameters", [])
            spec_path_params = [
                p["name"]
                for p in parameters
                if p.get("in") == "path" and p["name"] not in _EXCLUDED_PARAMS
            ]

            if spec_path_params != url_param_order:
                violations.append(
                    f"{method.upper()} {path_template}:\n"
                    f"  spec order (excl. task_id): {spec_path_params}\n"
                    f"  URL order  (excl. task_id): {url_param_order}",
                )

    assert not violations, (
        "Path parameters in OpenAPI spec are not in URL template order.\n\n"
        "Root cause: a path param is being extracted via Depends() instead of "
        "Annotated[str, Path(), AfterValidator(decode_path_param)]. FastAPI pushes "
        "Depends()-based params to the end of the spec parameter list, which reorders "
        "the generated API client's function signature and silently breaks call sites.\n\n"
        "Fix: convert the offending param to use AfterValidator inline instead of "
        "a Depends()-based decode helper.\n\n"
        "Violations:\n" + "\n".join(violations)
    )
