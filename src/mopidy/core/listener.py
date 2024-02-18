from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mopidy import listener

if TYPE_CHECKING:
    from mopidy.audio import PlaybackState
    from mopidy.models import Playlist, TlTrack
    from mopidy.types import DurationMs, Percentage, Uri


class CoreListener(listener.Listener):
    """Marker interface for recipients of events sent by the core actor.

    Any Pykka actor that mixes in this class will receive calls to the methods
    defined here when the corresponding events happen in the core actor. This
    interface is used both for looking up what actors to notify of the events,
    and for providing default implementations for those listeners that are not
    interested in all events.
    """

    def on_event(self, event: str, **kwargs: Any) -> None:
        """Called on all events.

        *MAY* be implemented by actor. By default, this method forwards the
        event to the specific event methods.

        :param event: the event name
        :param kwargs: any other arguments to the specific event handlers
        """
        # Just delegate to parent, entry mostly for docs.
        super().on_event(event, **kwargs)

    def track_playback_paused(
        self,
        tl_track: TlTrack,
        time_position: DurationMs,
    ) -> None:
        """Called whenever track playback is paused.

        *MAY* be implemented by actor.

        :param tl_track: the track that was playing when playback paused
        :param time_position: the time position in milliseconds
        """

    def track_playback_resumed(
        self,
        tl_track: TlTrack,
        time_position: DurationMs,
    ) -> None:
        """Called whenever track playback is resumed.

        *MAY* be implemented by actor.

        :param tl_track: the track that was playing when playback resumed
        :param time_position: the time position in milliseconds
        """

    def track_playback_started(self, tl_track: TlTrack) -> None:
        """Called whenever a new track starts playing.

        *MAY* be implemented by actor.

        :param tl_track: the track that just started playing
        """

    def track_playback_ended(
        self,
        tl_track: TlTrack,
        time_position: DurationMs,
    ) -> None:
        """Called whenever playback of a track ends.

        *MAY* be implemented by actor.

        :param tl_track: the track that was played before playback stopped
        :param time_position: the time position in milliseconds
        """

    def playback_state_changed(
        self,
        old_state: PlaybackState,
        new_state: PlaybackState,
    ) -> None:
        """Called whenever playback state is changed.

        *MAY* be implemented by actor.

        :param old_state: the state before the change
        :type old_state: string from :class:`mopidy.core.PlaybackState` field
        :param new_state: the state after the change
        :type new_state: string from :class:`mopidy.core.PlaybackState` field
        """

    def tracklist_changed(self) -> None:
        """Called whenever the tracklist is changed.

        *MAY* be implemented by actor.
        """

    def playlists_loaded(self) -> None:
        """Called when playlists are loaded or refreshed.

        *MAY* be implemented by actor.
        """

    def playlist_changed(self, playlist: Playlist) -> None:
        """Called whenever a playlist is changed.

        *MAY* be implemented by actor.

        :param playlist: the changed playlist
        :type playlist: :class:`mopidy.models.Playlist`
        """

    def playlist_deleted(self, uri: Uri) -> None:
        """Called whenever a playlist is deleted.

        *MAY* be implemented by actor.

        :param uri: the URI of the deleted playlist
        :type uri: string
        """

    def options_changed(self) -> None:
        """Called whenever an option is changed.

        *MAY* be implemented by actor.
        """

    def volume_changed(self, volume: Percentage) -> None:
        """Called whenever the volume is changed.

        *MAY* be implemented by actor.

        :param volume: the new volume in the range [0..100]
        :type volume: int
        """

    def mute_changed(self, mute: bool) -> None:
        """Called whenever the mute state is changed.

        *MAY* be implemented by actor.

        :param mute: the new mute state
        :type mute: boolean
        """

    def seeked(self, time_position: DurationMs) -> None:
        """Called whenever the time position changes by an unexpected amount, e.g.
        at seek to a new time position.

        *MAY* be implemented by actor.

        :param time_position: the position that was seeked to in milliseconds
        :type time_position: int
        """

    def stream_title_changed(self, title: str) -> None:
        """Called whenever the currently playing stream title changes.

        *MAY* be implemented by actor.

        :param title: the new stream title
        :type title: string
        """


class CoreEventEmitter(listener.EventEmitter[CoreListener]):
    @classmethod
    def track_playback_paused(
        cls,
        *,
        tl_track: TlTrack,
        time_position: DurationMs,
    ) -> None:
        return cls.emit(
            CoreListener,
            "track_playback_paused",
            tl_track=tl_track,
            time_position=time_position,
        )

    @classmethod
    def track_playback_resumed(
        cls,
        *,
        tl_track: TlTrack,
        time_position: DurationMs,
    ) -> None:
        return cls.emit(
            CoreListener,
            "track_playback_resumed",
            tl_track=tl_track,
            time_position=time_position,
        )

    @classmethod
    def track_playback_started(cls, *, tl_track: TlTrack) -> None:
        return cls.emit(CoreListener, "track_playback_started", tl_track=tl_track)

    @classmethod
    def track_playback_ended(
        cls,
        *,
        tl_track: TlTrack,
        time_position: DurationMs,
    ) -> None:
        return cls.emit(
            CoreListener,
            "track_playback_ended",
            tl_track=tl_track,
            time_position=time_position,
        )

    @classmethod
    def playback_state_changed(
        cls,
        *,
        old_state: PlaybackState,
        new_state: PlaybackState,
    ) -> None:
        return cls.emit(
            CoreListener,
            "playback_state_changed",
            old_state=old_state,
            new_state=new_state,
        )

    @classmethod
    def tracklist_changed(cls) -> None:
        return cls.emit(CoreListener, "tracklist_changed")

    @classmethod
    def playlists_loaded(cls) -> None:
        return cls.emit(CoreListener, "playlists_loaded")

    @classmethod
    def playlist_changed(cls, *, playlist: Playlist) -> None:
        return cls.emit(CoreListener, "playlist_changed", playlist=playlist)

    @classmethod
    def playlist_deleted(cls, *, uri: Uri) -> None:
        return cls.emit(CoreListener, "playlist_deleted", uri=uri)

    @classmethod
    def options_changed(cls) -> None:
        return cls.emit(CoreListener, "options_changed")

    @classmethod
    def volume_changed(cls, *, volume: Percentage) -> None:
        return cls.emit(CoreListener, "volume_changed", volume=volume)

    @classmethod
    def mute_changed(cls, *, mute: bool) -> None:
        return cls.emit(CoreListener, "mute_changed", mute=mute)

    @classmethod
    def seeked(cls, *, time_position: DurationMs) -> None:
        return cls.emit(CoreListener, "seeked", time_position=time_position)

    @classmethod
    def stream_title_changed(cls, *, title: str) -> None:
        return cls.emit(CoreListener, "stream_title_changed", title=title)
