from typing import Literal

from pydantic.fields import Field
from pydantic.types import NonNegativeInt

from mopidy.models import Ref, TlTrack
from mopidy.models._base import BaseModel
from mopidy.types import DurationMs, Percentage, TracklistId
from mopidy.types import PlaybackState as PlaybackStateEnum


class HistoryTrack(BaseModel):
    """A track that has been played back at a given timestamp.

    Internally used for save/load state.
    """

    model: Literal["HistoryTrack"] = Field(
        default="HistoryTrack",
        repr=False,
        serialization_alias="__model__",
    )

    # The timestamp when the track was played. Read-only.
    timestamp: NonNegativeInt

    # The track reference. Read-only.
    track: Ref


class HistoryState(BaseModel):
    """
    State of the history controller.

    Internally used for save/load state.
    """

    model: Literal["HistoryState"] = Field(
        default="HistoryState",
        repr=False,
        serialization_alias="__model__",
    )

    # The track history. Read-only.
    history: tuple[HistoryTrack, ...]


class MixerState(BaseModel):
    """
    State of the mixer controller.

    Internally used for save/load state.
    """

    model: Literal["MixerState"] = Field(
        default="MixerState",
        repr=False,
        serialization_alias="__model__",
    )

    # The volume. Read-only.
    volume: Percentage | None = None

    # The mute state. Read-only.
    mute: bool | None = None


class PlaybackState(BaseModel):
    """
    State of the playback controller.

    Internally used for save/load state.
    """

    model: Literal["PlaybackState"] = Field(
        default="PlaybackState",
        repr=False,
        serialization_alias="__model__",
    )

    # The tlid of current playing track. Read-only.
    tlid: TracklistId | None = Field(None, ge=1)

    # The playback position in milliseconds. Read-only.
    time_position: DurationMs

    # The playback state. Read-only.
    state: PlaybackStateEnum


class TracklistState(BaseModel):
    """
    State of the tracklist controller.

    Internally used for save/load state.
    """

    model: Literal["TracklistState"] = Field(
        default="TracklistState",
        repr=False,
        serialization_alias="__model__",
    )

    # The repeat mode. Read-only.
    repeat: bool

    # The consume mode. Read-only.
    consume: bool

    # The random mode. Read-only.
    random: bool

    # The single mode. Read-only.
    single: bool

    # The id of the track to play. Read-only.
    next_tlid: TracklistId

    # The list of tracks. Read-only.
    tl_tracks: tuple[TlTrack, ...]


class CoreState(BaseModel):
    """
    State of all Core controller.

    Internally used for save/load state.
    """

    model: Literal["CoreState"] = Field(
        default="CoreState",
        repr=False,
        serialization_alias="__model__",
    )

    # State of the history controller.
    history: HistoryState

    # State of the mixer controller.
    mixer: MixerState

    # State of the playback controller.
    playback: PlaybackState

    # State of the tracklist controller.
    tracklist: TracklistState
