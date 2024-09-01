from __future__ import annotations

import functools
import itertools
import typing

E = typing.TypeVar("E")
_KeyT = typing.TypeVar("_KeyT")
Choices = list[tuple[str, str]]
_MapVT = typing.TypeVar("_MapVT")


def chunked(items: typing.Iterable[E], size: int) -> typing.Generator[list[E], None, None]:
    result = []
    for value in items:
        result.append(value)
        if len(result) == size:
            yield result
            result = []

    if len(result):
        yield result


def attribute_reader(
    obj: typing.Any,
    attr: str | typing.Callable[[typing.Any], typing.Any],
    default: typing.Any = None,
) -> typing.Any:
    if callable(attr):
        return attr(obj)

    if hasattr(obj, "__getitem__"):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


class Collection(typing.Generic[E]):
    def __init__(self, items: typing.Iterable[E] | None = None) -> None:
        self._position = 0
        self.items = list(items or [])

    def first(self) -> E | None:
        """Return the first item from the collection."""
        try:
            return next(self)
        except StopIteration:
            return None

    def last(self) -> E | None:
        """Return the last item from the collection."""
        if len(self):
            return self[-1]
        return None

    def filter(self, fn: typing.Callable[[E], bool | None]) -> Collection[E]:
        """Filter collection items with `fn`."""
        return Collection([item for item in self if fn(item)])

    def find(self, fn: typing.Callable[[E], bool | None]) -> E | None:
        return self.filter(fn).first()

    def chunk(self, batch: int) -> typing.Generator[list[E], None, None]:
        """Split collection into chunks."""
        return chunked(self, batch)

    def pluck(self, key: str) -> Collection[typing.Any]:
        """Take a attribute/key named `key` from every item and return them in a new collection."""
        key = str(key)
        return Collection([attribute_reader(item, key, None) for item in self])

    def reverse(self) -> Collection[E]:
        """Reverse collection."""
        return Collection(reversed(self))

    def group_by(self, key: typing.Callable[[E], typing.Any] | str) -> dict[_KeyT, list[E]]:
        if isinstance(key, str):
            key = functools.partial(attribute_reader, attr=key)

        groups = itertools.groupby(sorted(self.items, key=key), key=key)
        return {k: list(v) for k, v in groups}

    def key_value(self, key: typing.Callable[[E], _KeyT] | str) -> dict[_KeyT, E]:
        if isinstance(key, str):
            key = functools.partial(attribute_reader, attr=key)

        return {key(item): item for item in self}

    def choices(
        self,
        label_attr: str | typing.Callable[[typing.Any], typing.Any] = "name",
        value_attr: str | typing.Callable[[typing.Any], typing.Any] = "id",
    ) -> Choices:
        return [(attribute_reader(item, value_attr), attribute_reader(item, label_attr)) for item in self]

    def choices_dict(
        self, label_col: str = "name", value_col: str = "id", label_key: str = "label", value_key: str = "value"
    ) -> list[dict[typing.Any, typing.Any]]:
        return [
            {value_key: attribute_reader(item, value_col), label_key: attribute_reader(item, label_col)}
            for item in self
        ]

    @typing.overload
    def __getitem__(self, index: slice) -> list[E]:  # pragma: no cover
        ...

    @typing.overload
    def __getitem__(self, index: int) -> E:  # pragma: no cover
        ...

    def __getitem__(self, index: int | slice) -> E | list[E]:
        if isinstance(index, slice):
            return list(self.items[index.start : index.stop : index.step])
        return self.items[index]

    def __setitem__(self, key: int, value: E) -> None:
        self.items.insert(key, value)

    def __delitem__(self, key: int) -> None:
        self.items.pop(key)

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> typing.Iterator[E]:
        return iter(self.items)

    def __contains__(self, item: E) -> bool:
        return item in self.items

    def __eq__(self, other: object) -> bool:
        if isinstance(other, typing.Sequence):
            other = self.__class__(other)

        if isinstance(other, Collection):
            return self.items == other.items
        raise ValueError(f"{type(self)} and {type(other)} are not comparable.")

    def __reversed__(self) -> Collection[E]:
        return Collection(reversed(list(self)))

    def __next__(self) -> E:
        if self._position < len(self):
            entity = self.items[self._position]
            self._position += 1
            return entity
        raise StopIteration

    def __str__(self) -> str:
        truncate = 10
        remainder = len(self) - truncate if len(self) > truncate else 0
        contents = ",".join(map(str, self[0:10]))
        suffix = f" and {remainder} items more" if remainder else ""
        return f"<Collection: [{contents}{suffix}]>"

    def __json__(self) -> list[E]:
        return list(self)
