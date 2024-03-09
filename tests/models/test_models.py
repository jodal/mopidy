import unittest

import pytest
from mopidy.models import (
    Album,
    Artist,
    Image,
    Playlist,
    Ref,
    SearchResult,
    TlTrack,
    Track,
)


class GenericReplaceTest(unittest.TestCase):
    def compare(self, orig, other):
        assert orig == other
        assert id(orig) == id(other)

    def test_replace_track_with_basic_values(self):
        track = Track(name="foo", uri="bar")
        other = track.replace(name="baz")
        assert other.name == "baz"
        assert other.uri == "bar"

    def test_replace_track_with_missing_values(self):
        track = Track(uri="bar")
        other = track.replace(name="baz")
        assert other.name == "baz"
        assert other.uri == "bar"

    def test_replace_track_with_private_internal_value(self):
        artist1 = Artist(name="foo")
        artist2 = Artist(name="bar")
        track = Track(artists=[artist1])
        other = track.replace(artists=[artist2])
        assert artist2 in other.artists

    def test_replace_track_with_invalid_key(self):
        with pytest.raises(TypeError):
            Track().replace(invalid_key=True)

    def test_replace_track_to_remove(self):
        track = Track(name="foo").replace(name=None)
        assert not hasattr(track, "_name")


class RefTest(unittest.TestCase):
    def test_uri(self):
        uri = "an_uri"
        ref = Ref.track(uri=uri, name="Foo")
        assert ref.uri == uri
        with pytest.raises(AttributeError):
            ref.uri = None

    def test_name(self):
        name = "a name"
        ref = Ref.track(uri="uri", name=name)
        assert ref.name == name
        with pytest.raises(AttributeError):
            ref.name = None

    # TODO: add these for the more of the models?
    def test_del_name(self):
        ref = Ref.track(uri="foo", name="foo")
        with pytest.raises(AttributeError):
            del ref.name

    def test_invalid_kwarg(self):
        with pytest.raises(TypeError):
            Ref(foo="baz")

    def test_repr_without_results(self):
        assert (
            repr(Ref(uri="uri", name="foo", type="artist"))
            == "Ref(uri='uri', name='foo', type='artist')"
        )

    def test_serialize_without_results(self):
        self.assertDictEqual(
            {"__model__": "Ref", "type": "track", "uri": "uri"},
            Ref.track(uri="uri", name=None).serialize(),
        )

    def test_type_constants(self):
        assert Ref.ALBUM == "album"
        assert Ref.ARTIST == "artist"
        assert Ref.DIRECTORY == "directory"
        assert Ref.PLAYLIST == "playlist"
        assert Ref.TRACK == "track"

    def test_album_constructor(self):
        ref = Ref.album(uri="foo", name="bar")
        assert ref.uri == "foo"
        assert ref.name == "bar"
        assert ref.type == Ref.ALBUM

    def test_artist_constructor(self):
        ref = Ref.artist(uri="foo", name="bar")
        assert ref.uri == "foo"
        assert ref.name == "bar"
        assert ref.type == Ref.ARTIST

    def test_directory_constructor(self):
        ref = Ref.directory(uri="foo", name="bar")
        assert ref.uri == "foo"
        assert ref.name == "bar"
        assert ref.type == Ref.DIRECTORY

    def test_playlist_constructor(self):
        ref = Ref.playlist(uri="foo", name="bar")
        assert ref.uri == "foo"
        assert ref.name == "bar"
        assert ref.type == Ref.PLAYLIST

    def test_track_constructor(self):
        ref = Ref.track(uri="foo", name="bar")
        assert ref.uri == "foo"
        assert ref.name == "bar"
        assert ref.type == Ref.TRACK


class ImageTest(unittest.TestCase):
    def test_uri(self):
        uri = "an_uri"
        image = Image(uri=uri)
        assert image.uri == uri
        with pytest.raises(AttributeError):
            image.uri = None

    def test_width(self):
        image = Image(uri="uri", width=100)
        assert image.width == 100
        with pytest.raises(AttributeError):
            image.width = None

    def test_height(self):
        image = Image(uri="uri", height=100)
        assert image.height == 100
        with pytest.raises(AttributeError):
            image.height = None

    def test_invalid_kwarg(self):
        with pytest.raises(TypeError):
            Image(uri="uri", foo="baz")


class ArtistTest(unittest.TestCase):
    def test_uri(self):
        uri = "an_uri"
        artist = Artist(uri=uri)
        assert artist.uri == uri
        with pytest.raises(AttributeError):
            artist.uri = None

    def test_name(self):
        name = "a name"
        artist = Artist(name=name)
        assert artist.name == name
        with pytest.raises(AttributeError):
            artist.name = None

    def test_musicbrainz_id(self):
        mb_id = "mb-id"
        artist = Artist(musicbrainz_id=mb_id)
        assert artist.musicbrainz_id == mb_id
        with pytest.raises(AttributeError):
            artist.musicbrainz_id = None

    def test_invalid_kwarg(self):
        with pytest.raises(TypeError):
            Artist(foo="baz")

    def test_invalid_kwarg_with_name_matching_method(self):
        with pytest.raises(TypeError):
            Artist(replace="baz")

        with pytest.raises(TypeError):
            Artist(serialize="baz")

    def test_repr(self):
        assert repr(Artist(uri="uri", name="name")) == "Artist(uri='uri', name='name')"

    def test_serialize(self):
        self.assertDictEqual(
            {"__model__": "Artist", "uri": "uri", "name": "name"},
            Artist(uri="uri", name="name").serialize(),
        )

    def test_serialize_falsy_values(self):
        self.assertDictEqual(
            {"__model__": "Artist", "uri": "", "name": ""},
            Artist(uri="", name="").serialize(),
        )


class AlbumTest(unittest.TestCase):
    def test_uri(self):
        uri = "an_uri"
        album = Album(uri=uri)
        assert album.uri == uri
        with pytest.raises(AttributeError):
            album.uri = None

    def test_name(self):
        name = "a name"
        album = Album(name=name)
        assert album.name == name
        with pytest.raises(AttributeError):
            album.name = None

    def test_artists(self):
        artist = Artist()
        album = Album(artists=[artist])
        assert artist in album.artists
        with pytest.raises(AttributeError):
            album.artists = None

    def test_num_tracks(self):
        num_tracks = 11
        album = Album(num_tracks=num_tracks)
        assert album.num_tracks == num_tracks
        with pytest.raises(AttributeError):
            album.num_tracks = None

    def test_num_discs(self):
        num_discs = 2
        album = Album(num_discs=num_discs)
        assert album.num_discs == num_discs
        with pytest.raises(AttributeError):
            album.num_discs = None

    def test_date(self):
        date = "1977-01-01"
        album = Album(date=date)
        assert album.date == date
        with pytest.raises(AttributeError):
            album.date = None

    def test_musicbrainz_id(self):
        mb_id = "mb-id"
        album = Album(musicbrainz_id=mb_id)
        assert album.musicbrainz_id == mb_id
        with pytest.raises(AttributeError):
            album.musicbrainz_id = None

    def test_invalid_kwarg(self):
        with pytest.raises(TypeError):
            Album(foo="baz")

    def test_repr_without_artists(self):
        assert (
            repr(Album(uri="uri", name="name"))
            == "Album(uri='uri', name='name', artists=frozenset())"
        )

    def test_repr_with_artists(self):
        assert (
            repr(Album(uri="uri", name="name", artists=frozenset({Artist(name="foo")})))
            == "Album(uri='uri', name='name', artists=frozenset({Artist(name='foo')}))"
        )

    def test_serialize_without_artists(self):
        assert Album(uri="uri", name="name").serialize() == {
            "__model__": "Album",
            "uri": "uri",
            "name": "name",
            "artists": [],
        }

    def test_serialize_with_artists(self):
        artist = Artist(name="foo")
        self.assertDictEqual(
            {
                "__model__": "Album",
                "uri": "uri",
                "name": "name",
                "artists": [artist.serialize()],
            },
            Album(uri="uri", name="name", artists=[artist]).serialize(),
        )


class TrackTest(unittest.TestCase):
    def test_uri(self):
        uri = "an_uri"
        track = Track(uri=uri)
        assert track.uri == uri
        with pytest.raises(AttributeError):
            track.uri = None

    def test_name(self):
        name = "a name"
        track = Track(name=name)
        assert track.name == name
        with pytest.raises(AttributeError):
            track.name = None

    def test_artists(self):
        artists = [Artist(name="name1"), Artist(name="name2")]
        track = Track(artists=artists)
        assert set(track.artists) == set(artists)
        with pytest.raises(AttributeError):
            track.artists = None

    def test_composers(self):
        artists = [Artist(name="name1"), Artist(name="name2")]
        track = Track(composers=artists)
        assert set(track.composers) == set(artists)
        with pytest.raises(AttributeError):
            track.composers = None

    def test_performers(self):
        artists = [Artist(name="name1"), Artist(name="name2")]
        track = Track(performers=artists)
        assert set(track.performers) == set(artists)
        with pytest.raises(AttributeError):
            track.performers = None

    def test_album(self):
        album = Album()
        track = Track(album=album)
        assert track.album == album
        with pytest.raises(AttributeError):
            track.album = None

    def test_track_no(self):
        track_no = 7
        track = Track(track_no=track_no)
        assert track.track_no == track_no
        with pytest.raises(AttributeError):
            track.track_no = None

    def test_disc_no(self):
        disc_no = 2
        track = Track(disc_no=disc_no)
        assert track.disc_no == disc_no
        with pytest.raises(AttributeError):
            track.disc_no = None

    def test_date(self):
        date = "1977-01-01"
        track = Track(date=date)
        assert track.date == date
        with pytest.raises(AttributeError):
            track.date = None

    def test_length(self):
        length = 137000
        track = Track(length=length)
        assert track.length == length
        with pytest.raises(AttributeError):
            track.length = None

    def test_bitrate(self):
        bitrate = 160
        track = Track(bitrate=bitrate)
        assert track.bitrate == bitrate
        with pytest.raises(AttributeError):
            track.bitrate = None

    def test_musicbrainz_id(self):
        mb_id = "mb-id"
        track = Track(musicbrainz_id=mb_id)
        assert track.musicbrainz_id == mb_id
        with pytest.raises(AttributeError):
            track.musicbrainz_id = None

    def test_invalid_kwarg(self):
        with pytest.raises(TypeError):
            Track(foo="baz")

    def test_repr_without_artists(self):
        assert (
            repr(Track(uri="uri", name="name")) == "Track(uri='uri', name='name', "
            "artists=frozenset(), composers=frozenset(), performers=frozenset())"
        )

    def test_repr_with_artists(self):
        assert (
            repr(Track(uri="uri", name="name", artists=[Artist(name="foo")]))
            == "Track(uri='uri', name='name', artists=[Artist(name='foo')], "
            "composers=frozenset(), performers=frozenset())"
        )

    def test_serialize_without_artists(self):
        assert Track(uri="uri", name="name").serialize() == {
            "__model__": "Track",
            "uri": "uri",
            "artists": [],
            "name": "name",
            "composers": [],
            "performers": [],
        }

    def test_serialize_with_artists(self):
        artist = Artist(name="foo")
        assert Track(uri="uri", name="name", artists=[artist]).serialize() == {
            "__model__": "Track",
            "uri": "uri",
            "name": "name",
            "artists": [artist.serialize()],
            "composers": [],
            "performers": [],
        }

    def test_serialize_with_album(self):
        album = Album(name="foo")
        assert Track(uri="uri", name="name", album=album).serialize() == {
            "__model__": "Track",
            "uri": "uri",
            "name": "name",
            "album": album.serialize(),
            "artists": [],
            "composers": [],
            "performers": [],
        }


class TlTrackTest(unittest.TestCase):
    def test_tlid(self):
        tlid = 123
        track = Track()
        tl_track = TlTrack(tlid=tlid, track=track)
        assert tl_track.tlid == tlid
        with pytest.raises(AttributeError):
            tl_track.tlid = None

    def test_track(self):
        tlid = 123
        track = Track()
        tl_track = TlTrack(tlid=tlid, track=track)
        assert tl_track.track == track
        with pytest.raises(AttributeError):
            tl_track.track = None

    def test_invalid_kwarg(self):
        with pytest.raises(TypeError):
            TlTrack(foo="baz")

    def test_positional_args(self):
        tlid = 123
        track = Track()
        tl_track = TlTrack(tlid, track)
        assert tl_track.tlid == tlid
        assert tl_track.track == track

    def test_iteration(self):
        tlid = 123
        track = Track()
        tl_track = TlTrack(tlid, track)
        (tlid2, track2) = tl_track
        assert tlid2 == tlid
        assert track2 == track

    def test_repr(self):
        assert (
            repr(TlTrack(tlid=123, track=Track(uri="uri")))
            == "TlTrack(tlid=123, track=Track(uri='uri', artists=frozenset(), "
            "composers=frozenset(), performers=frozenset()))"
        )

    def test_serialize(self):
        track = Track(uri="uri", name="name")
        self.assertDictEqual(
            {"__model__": "TlTrack", "tlid": 123, "track": track.serialize()},
            TlTrack(tlid=123, track=track).serialize(),
        )

    def test_eq(self):
        tlid = 123
        track = Track()
        tl_track1 = TlTrack(tlid=tlid, track=track)
        tl_track2 = TlTrack(tlid=tlid, track=track)
        assert tl_track1 == tl_track2
        assert hash(tl_track1) == hash(tl_track2)


class PlaylistTest(unittest.TestCase):
    def test_uri(self):
        uri = "an_uri"
        playlist = Playlist(uri=uri)
        assert playlist.uri == uri
        with pytest.raises(AttributeError):
            playlist.uri = None

    def test_name(self):
        name = "a name"
        playlist = Playlist(name=name)
        assert playlist.name == name
        with pytest.raises(AttributeError):
            playlist.name = None

    def test_tracks(self):
        tracks = [Track(), Track(), Track()]
        playlist = Playlist(tracks=tracks)
        assert list(playlist.tracks) == tracks
        with pytest.raises(AttributeError):
            playlist.tracks = None

    def test_length(self):
        tracks = [Track(), Track(), Track()]
        playlist = Playlist(tracks=tracks)
        assert playlist.length == 3

    def test_last_modified(self):
        last_modified = 1390942873000
        playlist = Playlist(last_modified=last_modified)
        assert playlist.last_modified == last_modified
        with pytest.raises(AttributeError):
            playlist.last_modified = None

    def test_with_new_uri(self):
        tracks = [Track()]
        last_modified = 1390942873000
        playlist = Playlist(
            uri="an uri",
            name="a name",
            tracks=tracks,
            last_modified=last_modified,
        )
        new_playlist = playlist.replace(uri="another uri")
        assert new_playlist.uri == "another uri"
        assert new_playlist.name == "a name"
        assert list(new_playlist.tracks) == tracks
        assert new_playlist.last_modified == last_modified

    def test_with_new_name(self):
        tracks = [Track()]
        last_modified = 1390942873000
        playlist = Playlist(
            uri="an uri",
            name="a name",
            tracks=tracks,
            last_modified=last_modified,
        )
        new_playlist = playlist.replace(name="another name")
        assert new_playlist.uri == "an uri"
        assert new_playlist.name == "another name"
        assert list(new_playlist.tracks) == tracks
        assert new_playlist.last_modified == last_modified

    def test_with_new_tracks(self):
        tracks = [Track()]
        last_modified = 1390942873000
        playlist = Playlist(
            uri="an uri",
            name="a name",
            tracks=tracks,
            last_modified=last_modified,
        )
        new_tracks = [Track(), Track()]
        new_playlist = playlist.replace(tracks=new_tracks)
        assert new_playlist.uri == "an uri"
        assert new_playlist.name == "a name"
        assert list(new_playlist.tracks) == new_tracks
        assert new_playlist.last_modified == last_modified

    def test_with_new_last_modified(self):
        tracks = [Track()]
        last_modified = 1390942873000
        new_last_modified = last_modified + 1000
        playlist = Playlist(
            uri="an uri",
            name="a name",
            tracks=tracks,
            last_modified=last_modified,
        )
        new_playlist = playlist.replace(last_modified=new_last_modified)
        assert new_playlist.uri == "an uri"
        assert new_playlist.name == "a name"
        assert list(new_playlist.tracks) == tracks
        assert new_playlist.last_modified == new_last_modified

    def test_invalid_kwarg(self):
        with pytest.raises(TypeError):
            Playlist(foo="baz")

    def test_repr_without_tracks(self):
        assert (
            repr(Playlist(uri="uri", name="name"))
            == "Playlist(uri='uri', name='name', tracks=())"
        )

    def test_repr_with_tracks(self):
        assert (
            repr(Playlist(uri="uri", name="name", tracks=[Track(name="foo")]))
            == "Playlist(uri='uri', name='name', tracks=[Track(name='foo', "
            "artists=frozenset(), composers=frozenset(), performers=frozenset())])"
        )

    def test_serialize_without_tracks(self):
        assert Playlist(uri="uri", name="name").serialize() == {
            "__model__": "Playlist",
            "uri": "uri",
            "name": "name",
            "tracks": (),
        }

    def test_serialize_with_tracks(self):
        track = Track(name="foo")
        self.assertDictEqual(
            {
                "__model__": "Playlist",
                "uri": "uri",
                "name": "name",
                "tracks": [track.serialize()],
            },
            Playlist(uri="uri", name="name", tracks=[track]).serialize(),
        )


class SearchResultTest(unittest.TestCase):
    def test_uri(self):
        uri = "an_uri"
        result = SearchResult(uri=uri)
        assert result.uri == uri
        with pytest.raises(AttributeError):
            result.uri = None

    def test_tracks(self):
        tracks = [Track(), Track(), Track()]
        result = SearchResult(tracks=tracks)
        assert list(result.tracks) == tracks
        with pytest.raises(AttributeError):
            result.tracks = None

    def test_artists(self):
        artists = [Artist(), Artist(), Artist()]
        result = SearchResult(artists=artists)
        assert list(result.artists) == artists
        with pytest.raises(AttributeError):
            result.artists = None

    def test_albums(self):
        albums = [Album(), Album(), Album()]
        result = SearchResult(albums=albums)
        assert list(result.albums) == albums
        with pytest.raises(AttributeError):
            result.albums = None

    def test_invalid_kwarg(self):
        with pytest.raises(TypeError):
            SearchResult(foo="baz")

    def test_repr_without_results(self):
        assert (
            repr(SearchResult(uri="uri"))
            == "SearchResult(uri='uri', tracks=(), artists=(), albums=())"
        )

    def test_serialize_without_results(self):
        assert SearchResult(uri="uri").serialize() == {
            "__model__": "SearchResult",
            "uri": "uri",
            "albums": (),
            "artists": (),
            "tracks": (),
        }
