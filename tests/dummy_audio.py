"""A dummy audio actor for use in tests.

This class implements the audio API in the simplest way possible. It is used in
tests of the core and backends.
"""


from typing import Callable

import pykka
from mopidy import audio
from mopidy.audio.listener import AudioEventEmitter
from mopidy.types import DurationMs, Percentage, Uri


def create_proxy(config=None, mixer=None):
    return DummyAudio.start(config, mixer).proxy()


# TODO: reset position on track change?
class DummyAudio(pykka.ThreadingActor):
    def __init__(self, config=None, mixer=None):
        super().__init__()
        self.state = audio.PlaybackState.STOPPED
        self._volume = 0
        self._position = 0
        self._source_setup_callback = None
        self._about_to_finish_callback = None
        self._uri = None
        self._stream_changed = False
        self._live_stream = False
        self._tags = {}
        self._bad_uris = set()

    def set_uri(self, uri, live_stream=False, download=False):
        assert self._uri is None, "prepare change not called before set"
        self._position = 0
        self._uri = uri
        self._stream_changed = True
        self._live_stream = live_stream
        self._tags = {}

    def get_position(self):
        return self._position

    def set_position(self, position: DurationMs) -> bool:
        self._position = position
        AudioEventEmitter.position_changed(position=position)
        return True

    def start_playback(self) -> bool:
        return self._change_state(audio.PlaybackState.PLAYING)

    def pause_playback(self):
        return self._change_state(audio.PlaybackState.PAUSED)

    def prepare_change(self) -> bool:
        self._uri = None
        self._source_setup_callback = None
        return True

    def stop_playback(self) -> bool:
        return self._change_state(audio.PlaybackState.STOPPED)

    def get_volume(self) -> Percentage:
        return self._volume

    def set_volume(self, volume: Percentage) -> bool:
        self._volume = volume
        return True

    def get_current_tags(self) -> dict:
        return self._tags

    def set_source_setup_callback(self, callback) -> None:
        self._source_setup_callback = callback

    def set_about_to_finish_callback(self, callback) -> None:
        self._about_to_finish_callback = callback

    def enable_sync_handler(self) -> None:
        pass

    def wait_for_state_change(self) -> None:
        pass

    def _change_state(self, new_state: audio.PlaybackState) -> bool:
        if not self._uri:
            return False

        if new_state == audio.PlaybackState.STOPPED and self._uri:
            self._stream_changed = True
            self._uri = None

        if self._stream_changed:
            self._stream_changed = False
            audio.AudioListener.send("stream_changed", uri=self._uri)

        if self._uri is not None:
            audio.AudioListener.send("position_changed", position=0)

        old_state, self.state = self.state, new_state
        audio.AudioListener.send(
            "state_changed",
            old_state=old_state,
            new_state=new_state,
            target_state=None,
        )

        if new_state == audio.PlaybackState.PLAYING:
            self._tags["audio-codec"] = ["fake info..."]
            AudioEventEmitter.tags_changed(tags=["audio-codec"])

        return self._uri not in self._bad_uris

    def trigger_fake_playback_failure(self, uri: Uri) -> None:
        self._bad_uris.add(uri)

    def trigger_fake_tags_changed(self, tags: dict[str, list]) -> None:
        self._tags.update(tags)
        AudioEventEmitter.tags_changed(tags=self._tags.keys())

    def get_source_setup_callback(self) -> Callable[[], None]:
        # This needs to be called from outside the actor or we lock up.
        def wrapper():
            if self._source_setup_callback:
                self._source_setup_callback()

        return wrapper

    def get_about_to_finish_callback(self) -> Callable[[], None]:
        # This needs to be called from outside the actor or we lock up.
        def wrapper():
            if self._about_to_finish_callback:
                self.prepare_change()
                self._about_to_finish_callback()

            if not self._uri or not self._about_to_finish_callback:
                self._tags = {}
                audio.AudioListener.send("reached_end_of_stream")
            else:
                audio.AudioListener.send("position_changed", position=0)
                audio.AudioListener.send("stream_changed", uri=self._uri)

        return wrapper
