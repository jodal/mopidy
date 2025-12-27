from __future__ import annotations

import pathlib
from collections.abc import Iterator, Mapping
from typing import Any, Literal, TypedDict, overload

LogColorName = Literal[
    "black",
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "white",
]
LogLevelName = Literal[
    "critical",
    "error",
    "warning",
    "info",
    "debug",
    "trace",
    "all",
]


class Config(Mapping):
    def __init__(self, data: dict[str, dict[str, Any]]) -> None:
        self._data = data

    @overload
    def __getitem__(self, key: Literal["core"]) -> CoreConfig: ...
    @overload
    def __getitem__(self, key: Literal["logging"]) -> LoggingConfig: ...
    @overload
    def __getitem__(self, key: Literal["loglevels"]) -> dict[LogLevelName, int]: ...
    @overload
    def __getitem__(
        self, key: Literal["logcolors"]
    ) -> dict[LogLevelName, LogColorName]: ...
    @overload
    def __getitem__(self, key: Literal["audio"]) -> AudioConfig: ...
    @overload
    def __getitem__(self, key: Literal["proxy"]) -> ProxyConfig: ...
    @overload
    def __getitem__(self, key: ...) -> ConfigSection: ...

    def __getitem__(self, key: str) -> ConfigSection:
        return ConfigSection(key, self._data.__getitem__(key))

    def __iter__(self) -> Iterator[str]:
        return self._data.__iter__()

    def __len__(self) -> int:
        return self._data.__len__()

    def __repr__(self) -> str:
        return f"Config({self._data!r})"


class ConfigSection(Mapping):
    def __init__(self, name: str, data: dict[str, Any]) -> None:
        self._name = name
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data.__getitem__(key)

    def __iter__(self) -> Iterator[str]:
        return self._data.__iter__()

    def __len__(self) -> int:
        return self._data.__len__()

    def __repr__(self) -> str:
        return f"ConfigSection({self._name!r}, {self._data!r})"


class CoreConfig(TypedDict):
    cache_dir: pathlib.Path
    config_dir: pathlib.Path
    data_dir: pathlib.Path
    max_tracklist_length: int
    restore_state: bool


class LoggingConfig(TypedDict):
    verbosity: int
    format: str
    color: bool
    config_file: pathlib.Path | None


class AudioConfig(TypedDict):
    mixer: str
    mixer_volume: int | None
    output: str
    buffer_time: int | None


class ProxyConfig(TypedDict):
    scheme: str | None
    hostname: str | None
    port: int | None
    username: str | None
    password: str | None
