from __future__ import annotations

import logging
import os
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

from cyclopts import App, Group, Parameter, Token
from platformdirs import PlatformDirs

import mopidy
from mopidy._app import logs
from mopidy._app.config import ConfigManager
from mopidy._app.extensions import ExtensionManager
from mopidy._app.main import create_app_dirs

logger = logging.getLogger(__name__)


def config_paths_default() -> list[Path]:
    dirs = PlatformDirs(appname="mopidy", appauthor="mopidy")
    # Use /etc instead of /etc/xdg unless XDG_CONFIG_DIRS is set.
    os.environ.setdefault("XDG_CONFIG_DIRS", "/etc")
    return [
        dirs.site_config_path / "mopidy.conf",
        dirs.user_config_path / "mopidy.conf",
    ]


def config_paths_display(value: list[Path]) -> str:
    return ", ".join(str(path) for path in value)


@Parameter(
    name="--config",
    help=(
        "Config files to use. "
        "Repeat parameter or separate values with colon to use multiple files. "
        "Later files have higher precedence."
    ),
    show_default=config_paths_display,
    negative="",
    n_tokens=1,
)
def config_paths_converter(_: type, tokens: Sequence[Token]) -> list[Path]:
    return [
        Path(path).expanduser() for token in tokens for path in token.value.split(":")
    ]


@Parameter(
    name=("--option", "-o"),
    help=(
        "Override config values. "
        "Repeat parameter to override multiple values. "
        "Format: SECTION/KEY=VALUE."
    ),
    negative="",
    n_tokens=1,
)
def config_overrides_converter(
    _: type, tokens: Sequence[Token]
) -> dict[str, dict[str, str]]:
    result = defaultdict(dict)
    for token in tokens:
        if "=" not in token.value:
            msg = f"Invalid config override: {token.value!r}"
            raise ValueError(msg)
        key, value = token.value.split("=", 1)
        if "/" not in key:
            msg = f"Invalid config override key: {key!r}"
            raise ValueError(msg)
        section, key = key.split("/", 1)
        result[section][key] = value
    return result


app = App(name="mopidy")
app.meta.group_parameters = Group("Global parameters", sort_key=0)


@app.meta.default
def meta(
    *tokens: Annotated[
        str,
        Parameter(show=False, allow_leading_hyphen=True),
    ],
    config_paths: Annotated[
        list[Path],
        Parameter(converter=config_paths_converter),
    ] = config_paths_default(),  # noqa: B008
    config_overrides: Annotated[
        dict[str, dict[str, str]] | None,
        Parameter(converter=config_overrides_converter),
    ] = None,
) -> None:
    logs.bootstrap_delayed_logging()
    logger.info(f"Starting Mopidy {mopidy.__version__}")

    extensions = ExtensionManager()
    extensions.init_commands(app)

    configs = ConfigManager(
        default=True,
        paths=config_paths,
        overrides=config_overrides,
        extensions=extensions,
    )
    configs.create_config_file()

    create_app_dirs(configs.validated_config)

    # Fully initialize logging
    # logs.setup_logging(
    #     configs.validated_config,
    #     base_verbosity_level,
    #     verbosity_level,
    # )

    # Run selected command
    app(tokens)


@app.default
def run_server() -> None:
    pass  # TODO


app.command(
    "mopidy._app.config:command",
    name="config",
    help="Show currently active configuration.",
)
app.command(
    "mopidy._app.deps:command",
    name="deps",
    help="Show dependencies and debug information.",
)
