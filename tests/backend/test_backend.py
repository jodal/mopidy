from unittest import mock

import pytest

from mopidy import backend
from mopidy.models import Track
from tests import dummy_backend


def test_library_default_get_images_impl():
    library = dummy_backend.DummyLibraryProvider(backend=None)

    assert library.get_images(["trackuri"]) == {}


def test_library_lookup_many_falls_back():
    library = backend.LibraryProvider(backend=None)
    library.lookup = mock.Mock()

    library.lookup_many(uris=["dummy1:a", "dummy1:b"])

    library.lookup.assert_has_calls(
        [
            mock.call("dummy1:a"),
            mock.call("dummy1:b"),
        ],
    )


@pytest.fixture
def provider():
    return backend.PlaylistsProvider(backend=None)


def test_playlists_as_list_default_impl(provider):
    with pytest.raises(NotImplementedError):
        provider.as_list()


def test_playlists_get_items_default_impl(provider):
    with pytest.raises(NotImplementedError):
        provider.get_items("some uri")


@pytest.fixture
def playback():
    audio = mock.Mock()
    audio.set_next_uri.return_value.get.return_value = None
    return backend.PlaybackProvider(audio=audio, backend=None)


def test_playback_queue_track_passes_the_translated_uri(playback):
    playback.translate_uri = mock.Mock(return_value="dummy:translated")

    assert playback.queue_track(Track(uri="dummy:a")) is True

    playback.audio.set_next_uri.assert_called_once_with(
        "dummy:translated",
        live_stream=False,
        download=False,
        source_setup_callback=playback.on_source_setup,
    )


def test_playback_queue_track_passes_the_buffering_hints(playback):
    playback.translate_uri = mock.Mock(return_value="dummy:a")
    playback.is_live = mock.Mock(return_value=True)
    playback.should_download = mock.Mock(return_value=True)

    playback.queue_track(Track(uri="dummy:a"))

    _, kwargs = playback.audio.set_next_uri.call_args
    assert kwargs["live_stream"] is True
    assert kwargs["download"] is True


def test_playback_queue_track_refuses_an_untranslatable_uri(playback):
    playback.translate_uri = mock.Mock(return_value=None)

    assert playback.queue_track(Track(uri="dummy:a")) is False

    playback.audio.set_next_uri.assert_not_called()


def test_playback_queue_track_does_not_set_the_global_source_callback(playback):
    playback.translate_uri = mock.Mock(return_value="dummy:a")

    playback.queue_track(Track(uri="dummy:a"))

    playback.audio.set_source_setup_callback.assert_not_called()
