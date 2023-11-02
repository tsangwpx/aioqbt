import logging
import sys

import pytest

from aioqbt import exc


def test_add_note(caplog: pytest.LogCaptureFixture):
    name = __name__
    logger = logging.getLogger(name)
    note = "**note_message**"

    try:
        try:
            raise ValueError
        except ValueError as ex:
            exc._add_note(ex, note, logger=logger)
            raise
    except ValueError as value_error:
        if sys.version_info >= (3, 11):
            assert any(note in s for s in value_error.__notes__), value_error.__notes__
        else:
            assert any(note in s for s in caplog.messages), caplog.messages
