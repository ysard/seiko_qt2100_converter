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
"""Parsing functions grouped in SeikoQT2100Parser class"""

# Standard imports
from pathlib import Path
from struct import unpack
from binascii import hexlify

# Custom imports
from seiko_converter import commons as cm

LOGGER = cm.logger()


class SeikoQT2100Parser:
    """Parser for the files produced by the Seiko QT-2100 Timegrapher device

    Attributes:
        :param raw_filename: Printer file to be opened.
        :param raw_data: Bytes read from the opened file.
        :param parsed_values: All the values emitted by the device in `ESC 1`
            messages.
            The range of values is [-999.999;+999.999]; Erroneous values due to
            measurement errors are None.
        :param parsed_timestamps: Timestamps for all the parsed values.
            Added by the Retroprinter programs in custom `ESC T` messages.
            In the case of an unedited raw file, these data are not present.

            .. note:: Currently only hh:mm:ss are stored in the raw file but only
            mm:ss are retrieved.

        :param print_mode: Print mode set on the device, prefixing all values in
            `ESC 1` messages.
        :param rate_mode: Current rate mode specified in the `ESC 0 `header message.
        :param acquisition_mode: Acquisition mode (Hz or Seconds) specified in
            the 3rd byte of value messages.
        :type raw_filename: str
        :type raw_data: bytes
        :type parsed_values: list[float, None]
        :type parsed_timestamps: list[str]
        :type print_mode: int
        :type rate_mode: int
        :type acquisition_mode: int

    Class attributes:
        :param RATE_MODES: Existing rate modes specified in the `ESC 0` header message.
        :param PRINT_MODES: Existing print modes specified in all `ESC 1` messages.
        :param ACQUISITION_MODES: Existing acquisition modes (Hz or Seconds)
        :type RATE_MODES: dict[int, str]
        :type PRINT_MODES: dict[int, str]
        :type ACQUISITION_MODES: dict[int, str]

    """

    RATE_MODES = {
        0: "10 SEC RATE SEC/DAY",
        1: "2 MIN RATE SEC/DAY",
        2: "1 SEC RATE SEC/DAY",
        3: "RATE SEC/DAY",
    }

    PRINT_MODES = {
        0: "C",
        1: "A 10S",
        2: "A 2M",
        3: "B 1S",
    }

    ACQUISITION_MODES = {
        0: "Seconds",
        32: "Hz",
    }

    def __init__(self, raw_filename):
        """Constructor

        :param raw_filename: Printer file to be parsed.
        """
        self.raw_filename = raw_filename
        self.raw_data = Path(self.raw_filename).read_bytes()

        self.parsed_values = []
        self.parsed_timestamps = []
        self.print_mode = None
        self.rate_mode = None
        self.acquisition_mode = None

    def parse(self):
        """Load the file content in memory

        Description of the printer modes and their file format.

        File format header:

            ``ESC 0 rate_mode``

        Global value format (8 bytes per value):

            ``ESC 1 print_mode flags unknown val1 val2 val3``

        Error format:

            ``ESC 1 print_mode flags``

        Print Modes:

            - Mode C:
                print_mode: 0

            - Mode B 1S:
                print_mode: 3

            - Modes A 1S/2M:
                print_mode: 1 or 2

        Flags:

            - 0x80: Measurement error
            - 0x20: Acquisition mode
                1: Hz (Quartz watch (LCD or stepper))
                0: Second (default)
            - 0x10: First value of a series ?
            - 0x01: Negative sign of the measured value

        RetroPrinter project adds timestamps in the file for every value with
        the following format (5 bytes):

            ``ESC T hours minutes seconds``
        """
        escmode = False
        seiko_mode = False
        timestamp_mode = False
        it_raw_data = iter(self.raw_data)

        def read_from_buffer(length):
            """Handy function to get a number of bytes from the file"""
            try:
                databytes = bytearray([next(it_raw_data) for _ in range(length)])
                return databytes
            except StopIteration:
                LOGGER.warning("Parsing end: Partial data => reject")

        def esc_tear_down():
            """Close ESC mode, waiting for next measure"""
            escmode = False
            seiko_mode = False
            timestamp_mode = False

        for databyte in it_raw_data:
            if databyte == 0x1B:
                escmode = True
                continue

            # Extract the header; ESC 0
            if escmode and databyte == ord("0"):
                LOGGER.debug("SEIKO header probe")
                data = read_from_buffer(1)
                if data is None:
                    break
                self.rate_mode = data[0]
                LOGGER.debug("Rate mode found: %s", self.get_rate_mode())
                esc_tear_down()
                continue

            # Begin to extract values only; ESC 1
            if escmode and databyte == ord("1"):
                LOGGER.debug("PROBE ESC 1 found")
                seiko_mode = True
                continue

            # Begin to extract timestamps + values; ESC T
            if escmode and databyte == ord("T"):
                LOGGER.debug("Timestamp found")
                timestamp_mode = True

                # Consume the timestamp + the ESC 1 header that follows
                # the next iteration will be at the same point as if there had
                # been no timestamp: mode byte
                data = read_from_buffer(5)
                if data is None:
                    break

                data = unpack(">BBBH", data)
                hours, minutes, seconds, esc1_header = data
                assert esc1_header == 0x1B31

                LOGGER.debug("> timestamp: %s:%s:%s", hours, minutes, seconds)
                self.parsed_timestamps.append(
                    ":".join(map(lambda val: format(val, "#02"), (minutes, seconds)))
                )
                continue

            # Extract values
            if escmode and (seiko_mode or timestamp_mode):
                print_mode = databyte
                assert print_mode in (0, 1, 2, 3), f"Unknown mode {print_mode}"
                self.print_mode = print_mode
                LOGGER.debug("Print mode found: %s", self.get_print_mode())

                data = read_from_buffer(1)
                if data is None:
                    break
                elif data == b"\x1b":
                    LOGGER.error("Unexpected ESC command encountered")
                    break

                byte3 = unpack("B", data)[0]

                # 1st bit is the sign flag
                sign = -1 if byte3 & 1 else 1

                if byte3 & 128 == 128:  # 0x80
                    sign_chr = "+" if sign else "-"
                    LOGGER.debug("Scale ERROR %s", sign_chr)
                    # => no value, Skip value
                    # self.parsed_values.append(f"{sign_chr} OUT OF RANGE")
                    self.parsed_values.append(None)
                    esc_tear_down()
                    continue

                # TODO: For now byte4 is not used
                ukn_flag = read_from_buffer(1)

                # Remove the sign flag, and get the mode in use
                self.acquisition_mode = byte3 & 32  # 0x20
                if self.acquisition_mode in self.ACQUISITION_MODES:
                    # 0 or 32 (0x20)
                    LOGGER.debug(
                        "Acquisition mode: %s; %d",
                        self.get_acquisition_mode(),
                        self.acquisition_mode,
                    )
                else:
                    LOGGER.error("Acquisition mode: Unknwon; %d", self.acquisition_mode)
                    raise ValueError

                if byte3 & 16 == 16:  # 0x10
                    # ex: in 0x30 with 0x20 acquisition mode (Hz)
                    LOGGER.warning("1st val of Hz mode ?; %s", hex(byte3 & ~1))

                data = read_from_buffer(3)
                if data is None:
                    break

                try:
                    # Extract values: val1, val2, val3
                    measure = int(hexlify(data)) / 1000 * sign # !!!! uncertain conversion
                    LOGGER.debug("> %s", measure)
                except ValueError:
                    LOGGER.error("Unexpected end of data")
                    break

                self.parsed_values.append(measure)

            esc_tear_down()

        LOGGER.info("Parsed %s values", len(self.parsed_values))

    def get_rate_mode(self):
        """Get the current rate mode of the file (human-readable form)

        See :meth:`RATE_MODES`.
        """
        return SeikoQT2100Parser.RATE_MODES[self.rate_mode]

    def get_print_mode(self):
        """Get the last print mode seen in the values (human-readable form)

        Should be the same for all the dataset...

        See :meth:`PRINT_MODES`.
        """
        return SeikoQT2100Parser.PRINT_MODES[self.print_mode]

    def get_acquisition_mode(self):
        """Get the last acquisition mode seen in the values (human-readable form)

        Should be the same for all the dataset...

        See :meth:`ACQUISITION_MODES`.
        """
        return SeikoQT2100Parser.ACQUISITION_MODES[self.acquisition_mode]
