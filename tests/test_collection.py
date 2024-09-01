import pytest

from starlette_sqlalchemy.collection import Collection


def test_first() -> None:
    collection = Collection([1, 2, 3])
    assert collection.first() == 1


def test_first_on_empty() -> None:
    collection = Collection[int]([])
    assert collection.first() is None


def test_last() -> None:
    collection = Collection([1, 2, 3])
    assert collection.last() == 3


def test_find() -> None:
    collection = Collection([1, 2, 3])
    assert collection.find(lambda x: x == 2) == 2


def test_last_on_empty() -> None:
    collection = Collection[int]([])
    assert collection.last() is None


def test_reverse() -> None:
    collection = Collection([1, 2, 3])
    assert collection.reverse() == Collection([3, 2, 1])


def test_chunk() -> None:
    collection = Collection([1, 2, 3, 4, 5, 6, 7])
    chunks = list(collection.chunk(2))
    assert len(chunks) == 4
    assert chunks[0] == [1, 2]
    assert chunks[1] == [3, 4]
    assert chunks[2] == [5, 6]
    assert chunks[3] == [7]


def test_chunk_empty() -> None:
    collection = Collection[int]([])
    chunks = list(collection.chunk(2))
    assert len(chunks) == 0


def test_pluck_on_dicts() -> None:
    collection = Collection([{"a": 1}, {"a": 2}])
    assert list(collection.pluck("a")) == [1, 2]


def test_pluck_on_classes() -> None:
    class Class:
        def __init__(self, val: int) -> None:
            self.a = val

    collection = Collection([Class(1), Class(2)])
    assert list(collection.pluck("a")) == [1, 2]


def test_filter() -> None:
    def _callback(x: int) -> bool:
        return x == 2

    collection = Collection([1, 2, 3])
    assert list(collection.filter(_callback)) == [2]


def test_group_by() -> None:
    collection = Collection(
        [
            {"id": 1},
            {"id": 2},
            {"id": 3},
            {"id": 3},
        ]
    )
    assert collection.group_by(lambda x: x["id"]) == {
        1: [{"id": 1}],
        2: [{"id": 2}],
        3: [{"id": 3}, {"id": 3}],
    }


def test_group_by_string_key() -> None:
    collection = Collection(
        [
            {"id": 1},
            {"id": 2},
            {"id": 3},
            {"id": 3},
        ]
    )
    assert collection.group_by("id") == {
        1: [{"id": 1}],
        2: [{"id": 2}],
        3: [{"id": 3}, {"id": 3}],
    }


def test_key_value() -> None:
    collection = Collection(
        [
            {"id": 1},
            {"id": 2},
            {"id": 3},
            {"id": 3},
        ]
    )
    assert collection.key_value(lambda x: x["id"]) == {
        1: {"id": 1},
        2: {"id": 2},
        3: {"id": 3},
    }


def test_key_value_by_string_key() -> None:
    collection = Collection(
        [
            {"id": 1},
            {"id": 2},
            {"id": 3},
            {"id": 3},
        ]
    )
    assert collection.key_value("id") == {1: {"id": 1}, 2: {"id": 2}, 3: {"id": 3}}


def test_countable() -> None:
    collection = Collection([1, 2, 3])
    assert len(collection) == 3


def test_set_by_index() -> None:
    collection = Collection([1, 2, 3])
    collection[2] = 4
    assert list(collection) == [1, 2, 4, 3]


def test_get_by_index() -> None:
    collection = Collection([1, 2, 3])
    assert collection[1] == 2


def test_get_slice() -> None:
    collection = Collection([1, 2, 3])
    assert collection[1:] == [2, 3]


def test_delete_by_index() -> None:
    collection = Collection([1, 2, 3])
    del collection[1]
    assert list(collection) == [1, 3]


def test_contains() -> None:
    collection = Collection([1, 2, 3])
    assert 2 in collection


def test_stringable() -> None:
    collection = Collection([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    assert str(collection) == "<Collection: [1,2,3,4,5,6,7,8,9,10 and 1 items more]>"


def test_choices() -> None:
    items = [
        {"item_id": "1", "item_name": "one"},
        {"item_id": "2", "item_name": "two"},
        {"item_id": "3", "item_name": "three"},
    ]
    assert Collection(items).choices("item_name", "item_id") == [("1", "one"), ("2", "two"), ("3", "three")]


def test_choices_attr_getter() -> None:
    items = [
        {"item_id": "1", "item_name": "one"},
        {"item_id": "2", "item_name": "two"},
        {"item_id": "3", "item_name": "three"},
    ]
    assert Collection(items).choices(
        label_attr=lambda x: x["item_name"],
        value_attr=lambda x: x["item_id"],
    ) == [("1", "one"), ("2", "two"), ("3", "three")]


def test_choices_dict() -> None:
    items = [
        {"item_id": "1", "item_name": "one"},
        {"item_id": "2", "item_name": "two"},
        {"item_id": "3", "item_name": "three"},
    ]
    assert Collection(items).choices_dict("item_name", "item_id") == [
        {"value": "1", "label": "one"},
        {"value": "2", "label": "two"},
        {"value": "3", "label": "three"},
    ]


def test_iter_resets_counter() -> None:
    collection = Collection([1, 2, 3])
    assert list(collection) == [1, 2, 3]
    assert list(collection) == [1, 2, 3]


def test_compares() -> None:
    collection = Collection([1, 2, 3])
    collection2 = Collection([1, 2, 3])
    assert collection == collection2

    assert collection == [1, 2, 3]

    with pytest.raises(ValueError, match="not comparable"):
        collection == 1  # noqa


def test_jsonable() -> None:
    collection = Collection([1, 2, 3])
    assert collection.__json__() == [1, 2, 3]
