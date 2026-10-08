"""Field types the standalone config file and every sink target's config share.

Kept apart from `discovery_config` because that module imports the sink targets to
know which destinations exist, and each target's config needs these: shared from
either side, the two would import each other.
"""

from pathlib import Path
from typing import Annotated, Any, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, SecretStr, ValidationInfo

# The validation context key carrying the config file's directory, which relative paths
# resolve against -- so a config and the files beside it can be mounted anywhere
# together.
BASE_DIR_CONTEXT = "base_dir"


class StrictModel(BaseModel):
    # Forbidding unknown keys is what turns a misspelt key into a startup error instead
    # of a setting that is silently ignored.
    model_config = ConfigDict(extra="forbid", frozen=True)


def read_file_reference(value: Any, base_dir: Optional[Path], strip: bool) -> str:
    """The contents of the file a `{file: path}` value names.

    Secrets are trimmed, because a mounted secret almost always ends in a newline its
    author never meant, and a token with one fails authentication with an error that
    does not say so. A query is kept exactly as written.
    """
    if not isinstance(value, dict) or set(value) != {"file"}:
        raise ValueError("expected a string or {file: <path>}")
    if not isinstance(value["file"], str):
        raise ValueError("expected {file: <path>} with a string path")
    path = Path(value["file"])
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    try:
        # UTF-8 whatever the locale: the engine's image runs under C/POSIX, where the
        # default would refuse or mangle any non-ASCII byte in a key or catalog.
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        # The OS error names the path and why, and nothing that was in the file.
        raise ValueError(f"could not read {path}: {e.strerror}") from None
    except UnicodeDecodeError:
        raise ValueError(f"{path} is not valid UTF-8") from None
    return text.strip() if strip else text


def _secret_value(value: Any, info: ValidationInfo) -> Any:
    """The credential, trimmed, and never empty.

    Empty is refused rather than sent. `${NAME}` substitutes whatever the environment
    holds, and Compose sets a variable that an env file lists with no value, so a
    template's blank `TOKEN=` would otherwise start an engine that authenticates with
    nothing and fails every delivery -- where an unset one stops it at startup, naming
    the variable.
    """
    if isinstance(value, dict):
        base_dir = (info.context or {}).get(BASE_DIR_CONTEXT)
        value = read_file_reference(value, base_dir, strip=True)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
    return value


# A credential given inline or as `{file: path}`, held as a SecretStr so it never
# appears in a repr.
Secret = Annotated[SecretStr, BeforeValidator(_secret_value)]
