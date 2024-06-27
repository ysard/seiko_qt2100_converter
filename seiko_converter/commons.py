#!/usr/bin/env python3
#  Seiko Converter is a software allowing to generate graphs based on the raw
#  data produced by the Seiko Qt-2100 Timegrapher device.
#  Copyright (C) 2024  Ysard
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Logger settings and project constants"""

# Standard imports
from logging.handlers import RotatingFileHandler
import logging


# Logging
LOGGER_NAME = "seiko-converter"
LOG_LEVEL = "INFO"

################################################################################
_logger = logging.getLogger(LOGGER_NAME)
_logger.setLevel(LOG_LEVEL)


def logger(name=LOGGER_NAME):
    """Return logger of given name, without initialize it.

    Equivalent of logging.getLogger() call.
    """
    logger_obj = logging.getLogger(name)
    fmt_str = "%(levelname)s: [%(filename)s:%(lineno)s:%(funcName)s()] %(message)s"
    logging.basicConfig(format=fmt_str)
    return logger_obj


def log_level(level):
    """Set terminal/file log level to the given one.

    .. note:: Don't forget the propagation system of messages:
        From logger to handlers. Handlers receive log messages only if
        the main logger doesn't filter them.
    """
    level = level.upper()
    if level == "NONE":
        logging.disable()
        return
    # Main logger
    _logger.setLevel(level)
    # Handlers
    [
        handler.setLevel(level)
        for handler in _logger.handlers
        if handler.__class__
        in (logging.StreamHandler, logging.handlers.RotatingFileHandler)
    ]
