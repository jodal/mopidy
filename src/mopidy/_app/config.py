from __future__ import annotations

import configparser
import logging
import os
import re
from collections.abc import Generator, Iterator, Mapping
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, cast

import mopidy
from mopidy._app.extensions import ExtensionManager
from mopidy._lib import paths
from mopidy.config import Config, DeprecatedValue, read

from . import config_schemas

if TYPE_CHECKING:
    from .config_schemas import ConfigSchemas

logger = logging.getLogger(__name__)


def command() -> None:
    config_manager = ConfigManager.get_default()
    output = config_manager.format(
        with_header=False,
        hide_secrets=True,
        comment_out_defaults=False,
    )

    # Throw away all bytes that are not valid UTF-8 before printing
    output = output.encode(errors="surrogateescape").decode(errors="replace")

    print(output)  # noqa: T201


type ConfigOverrides = dict[str, dict[str, str]]
type ConfigComments = dict[str, dict[str, Any]]
type RawConfig = dict[str, dict[str, Any]]


class ConfigManager:
    _default_manager: ClassVar[ContextVar[ConfigManager | None]] = ContextVar(
        "ConfigManager", default=None
    )

    @classmethod
    def get_default(cls) -> ConfigManager:
        config_manager = cls._default_manager.get()
        if config_manager is None:
            msg = "ConfigManager not set in context"
            raise RuntimeError(msg)
        return config_manager

    def __init__(
        self,
        *,
        default: bool,
        paths: list[Path],
        overrides: ConfigOverrides | None = None,
        extensions: ExtensionManager,
    ) -> None:
        self._paths = paths
        self._overrides: ConfigOverrides = overrides or {}
        self._extensions = extensions

        if default:
            if self._default_manager.get():
                msg = "ConfigManager already set in context"
                raise RuntimeError(msg)
            self._default_manager.set(self)

    @property
    def defaults(self) -> list[str]:
        return [
            read(Path(__file__).parent / "default.conf"),
            *self._extensions.config_defaults,
        ]

    @property
    def schemas(self) -> ConfigSchemas:
        return [
            *config_schemas.schemas,
            *self._extensions.config_schemas,
        ]

    @property
    def raw_config(self) -> RawConfig:
        parser = configparser.RawConfigParser(inline_comment_prefixes=(";",))

        # TODO: simply return path to config file for defaults so we can load it
        # all in the same way?
        logger.info("Loading config from builtin defaults")
        for default in self.defaults:
            if isinstance(default, bytes):
                default = default.decode()
            parser.read_string(default)

        # Load config from a series of config files
        for path in self._paths:
            path = paths.expand_path(path)
            # TODO: Drop support for directories?
            if path.is_dir():
                for entry in path.iterdir():
                    if entry.is_file() and entry.suffix == ".conf":
                        self._read_config_file(parser, entry)
            else:
                self._read_config_file(parser, path)

        if self._overrides:
            logger.info("Loading config from command line options")
            parser.read_dict(self._overrides)

        return {section: dict(parser.items(section)) for section in parser.sections()}

    def _read_config_file(
        self,
        parser: configparser.RawConfigParser,
        file_path: Path,
    ) -> None:
        if not file_path.exists():
            logger.debug(
                f"Loading config from {file_path.as_uri()} failed; it does not exist",
            )
            return
        if not os.access(str(file_path), os.R_OK):
            logger.warning(
                f"Loading config from {file_path.as_uri()} failed; read permission missing",
            )
            return

        try:
            logger.info(f"Loading config from {file_path.as_uri()}")
            with file_path.open("r") as fh:
                parser.read_file(fh)
        except configparser.MissingSectionHeaderError:
            logger.warning(
                f"Loading config from {file_path.as_uri()} failed; "
                f"it does not have a config section",
            )
        except configparser.ParsingError as e:
            linenos = ", ".join(str(lineno) for lineno, line in e.errors)
            logger.warning(
                f"Config file {file_path.as_uri()} has errors; "
                f"line {linenos} has been ignored",
            )
        except OSError:
            # TODO: if this is the initial load of logging config we might not
            # have a logger at this point, we might want to handle this better.
            logger.debug(f"Config file {file_path.as_uri()} not found; skipping")

    @property
    def validated_config(self) -> Config:
        config, _errors = self._validate()
        return config

    @property
    def errors(self) -> ConfigComments:
        _config, errors = self._validate()
        return errors

    def _validate(self) -> tuple[Config, ConfigComments]:
        schemas = self.schemas
        raw_config = self.raw_config
        validated_config: RawConfig = {}
        errors: ConfigComments = {}

        for schema in schemas:
            values = raw_config.get(schema.name, {})
            result, error = schema.deserialize(values)
            if error:
                errors[schema.name] = error
            if result:
                validated_config[schema.name] = result

        for section in set(self.raw_config) - {schema.name for schema in self.schemas}:
            logger.warning(
                f"Ignoring config section {section!r} "
                f"because no matching extension was found",
            )

        return cast(Config, validated_config), errors

    def create_config_file(self) -> Path | None:
        """Initialize whatever the last config file is with defaults."""
        config_file = self._paths[-1]
        if config_file.exists():
            return None

        initial_configs = ConfigManager(
            default=False,  # This is not the default config manager
            paths=[],  # Avoid loading existing files
            overrides={},  # Skip any overrides
            extensions=self._extensions,
        )

        try:
            paths.get_or_create_file(
                config_file,
                mkdir=True,
                content=initial_configs.format(
                    with_header=True, hide_secrets=True, comment_out_defaults=True
                ),
                errors="surrogateescape",
            )
        except OSError as exc:
            logger.warning(
                f"Unable to initialize {config_file.as_uri()} "
                f"with default config: {exc}"
            )
            return None

        logger.info(f"Initialized {config_file.as_uri()} with default config")
        return config_file

    def format(
        self,
        *,
        with_header: bool = False,
        hide_secrets: bool = True,
        comment_out_defaults: bool = False,
        comments: ConfigComments | None = None,
    ) -> str:
        return "\n".join(
            self._format_generator(
                with_header=with_header,
                hide_secrets=hide_secrets,
                comment_out_defaults=comment_out_defaults,
                comments=comments or {},
            )
        ).strip()

    def _format_generator(
        self,
        *,
        with_header: bool,
        hide_secrets: bool,
        comment_out_defaults: bool,
        comments: ConfigComments,
    ) -> Generator[str]:
        if with_header:
            versions = [
                f"mopidy {mopidy.__version__}",
                *[
                    f"{ed.extension.dist_name} {ed.extension.version}"
                    for ed in self._extensions.installed
                ],
            ]
            yield _CONFIG_FILE_HEADER.format(
                versions="\n#   ".join(versions),
            )

        validated_config = self.validated_config
        for schema in self.schemas:
            serialized = schema.serialize(
                validated_config.get(schema.name, {}),
                display=hide_secrets,
            )
            if not serialized:
                continue
            yield f"[{schema.name}]"
            for key, value in serialized.items():
                if isinstance(value, DeprecatedValue):
                    continue
                comment = comments.get(schema.name, {}).get(key, "")
                line = f"{key} ="
                if value is not None:
                    line += " " + value
                if comment:
                    line += "  ; " + comment.capitalize()
                if comment_out_defaults:
                    line = re.sub(r"^", "#", line, flags=re.MULTILINE)
                yield line
            yield ""


_CONFIG_FILE_HEADER = """
# For further information about options in this file see:
#   https://docs.mopidy.com/
#
# The initial commented out values reflect the defaults as of:
#   {versions}
#
# Available options and defaults might have changed since then,
# run `mopidy config` to see the current effective config and
# `mopidy --version` to check the current version.
"""


class ReadOnlyDict(Mapping):
    def __init__(self, data: Config | dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: Any) -> Any:
        item = self._data.__getitem__(key)
        if isinstance(item, dict):
            return ReadOnlyDict(item)
        return item

    def __iter__(self) -> Iterator[str]:
        return self._data.__iter__()

    def __len__(self) -> int:
        return self._data.__len__()

    def __repr__(self) -> str:
        return f"ReadOnlyDict({self._data!r})"
