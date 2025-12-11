import json
import logging
import os
import re
import subprocess
from typing import Generator

from fastapi.openapi.utils import get_openapi

from server import get_app_with_routes

logger = logging.getLogger()


def find_url(input_data: str) -> str | None:
    if result := re.search(r"[GET|POST|DELETE|PUT|PATCH] (\/.*$)", input_data):
        return result.group(1)
    return None


def analyze_openapi_diff(input_data: tuple[str, str, str]) -> str:
    if input_data[0].startswith("error"):
        changelog_message = "- **BREAKING CHANGE**"
    else:
        changelog_message = "- **CHANGE**"

    url = find_url(input_data=input_data[1])
    if url:
        changelog_message += f" for **URL**: {find_url(input_data=input_data[1])}"
    elif "api-schema-removed" in input_data[0]:
        changelog_message += " for Component/Schema:"
    changelog_message += input_data[2]
    changelog_message += "\n"
    return changelog_message


def get_output_of_openapi_diff(
    current_openapi_path,
    new_openapi_path,
) -> Generator[tuple[str, str, str], None, None] | None:
    logger.info(f"Current openapi path: {current_openapi_path}")
    logger.info(f"New openapi path: {new_openapi_path}")
    output = subprocess.run(
        ["oasdiff", "changelog", current_openapi_path, new_openapi_path],
        capture_output=True,
    )
    logger.info(f"Return code of the command: {output.returncode}")
    if output.returncode != 0:
        stdout_text = output.stdout.decode("utf-8")
        stderr_text = output.stderr.decode("utf-8")
        raise ValueError(
            f"Something wrong happened during diff generation. Return code: {output.returncode}\nSTDOUT: {stdout_text}\nSTDERR: {stderr_text}",
        )

    raw_changelog = [
        line
        for line in output.stdout.decode("utf-8").replace("\t", " ").split("\n")
        if line
    ]

    if not raw_changelog:
        logger.info("No changes in OpenAPI schema.")
        return []
    # Here we are returning the generator that iterates over output of the oasdiff application from shell
    # Output of this application contains summary in first line, and change in every 3 lines, that why
    # we are grouping 3 objects from list, that we could iterate over in generator.
    logger.info(f"OpenAPI schema was updated. Summary: {raw_changelog[0]}")
    return zip(*(iter(raw_changelog[1:]),) * 3)


def generate_new_openapi(path: str) -> None:
    logger.info("Getting current version of OpenAPI schema.")
    app = get_app_with_routes()
    with open(path, "w+") as f:
        json.dump(
            get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                description=app.description,
                routes=app.routes,
            ),
            f,
            indent=4,
        )


def main():
    path_directory = os.path.dirname(os.path.abspath(__name__))
    if path_directory.endswith("genai-engine"):
        path_directory = os.path.dirname(path_directory)
    new_openapi_path = os.path.join(path_directory, "genai-engine/new.openapi.json")
    generate_new_openapi(new_openapi_path)
    logger.info(f"OpenAPI schema generated and saved to {new_openapi_path}")


if __name__ == "__main__":
    main()
