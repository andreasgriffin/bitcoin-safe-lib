import logging

from bitcoin_safe_lib.storage import SaveAllClass


class ExampleSaveable(SaveAllClass):
    VERSION = "1.0.0"

    def __init__(self, value: str, optional: str | None = None) -> None:
        self.value = value
        self.optional = optional


def test_from_dumps_prefers_dct_values_over_class_kwargs(caplog) -> None:
    json_string = (
        '{"__class__":"ExampleSaveable","VERSION":"1.0.0","value":"from_dct","optional":"from_json"}'
    )

    with caplog.at_level(logging.ERROR, logger="bitcoin_safe_lib.storage"):
        obj = ExampleSaveable._from_dumps(
            json_string,
            class_kwargs={"ExampleSaveable": {"value": "from_kwargs", "extra": "unused"}},
        )

    assert obj.value == "from_dct"
    assert obj.optional == "from_json"
    assert "Duplicate deserialization keys" in caplog.text
    assert "ExampleSaveable" in caplog.text
    assert "value" in caplog.text
