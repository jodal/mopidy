from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal, NewType, TypeVar

if TYPE_CHECKING:
    from typing import TypeAlias

# Integer types
Percentage = NewType("Percentage", int)
DurationMs = NewType("DurationMs", int)

# URI types
Uri = NewType("Uri", str)
UriScheme = NewType("UriScheme", str)

# Query types
F = TypeVar("F")
QueryValue: TypeAlias = str | int
Query: TypeAlias = dict[F, Iterable[QueryValue]]

# Types for distinct queries
DistinctField: TypeAlias = Literal[
    "uri",
    "track_name",
    "album",
    "artist",
    "albumartist",
    "composer",
    "performer",
    "track_no",
    "genre",
    "date",
    "comment",
    "disc_no",
    "musicbrainz_albumid",
    "musicbrainz_artistid",
    "musicbrainz_trackid",
]

# Types for search queries
SearchField: TypeAlias = DistinctField | Literal["any"]
SearchQuery: TypeAlias = dict[SearchField, Iterable[QueryValue]]

# Tracklist types
TracklistId = NewType("TracklistId", Annotated[int, msgspec.Meta(ge=0)])
TracklistField: TypeAlias = Literal[
    "tlid",
    "uri",
    "name",
    "genre",
    "comment",
    "musicbrainz_id",
]

# Superset of all fields that can be used in a query
QueryField: TypeAlias = DistinctField | SearchField | TracklistField


