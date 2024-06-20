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
# Standard imports
from pathlib import Path
from struct import unpack
from binascii import hexlify
from functools import partial
import csv

# Custom imports
import statistics as stat
import pandas as pd
import matplotlib.pyplot as plt
from numpy import cumsum


class SeikoQT2100Parser:
    """Parser for the files produced by the Seiko QT-2100 Timegrapher device

    Attributes:
        :param raw_filename: File to be opened.
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
        :type raw_filename: str
        :type raw_data: bytes
        :type parsed_values: list[float, None]
        :type parsed_timestamps: list[str]
        :type print_mode:
        :type rate_mode:

    Class attributes:
        :param RATE_MODES: Existing rate modes specified in the `ESC 0` header message.
        :param PRINT_MODES: Existing print modes specified in all `ESC 1` messages.
        :type RATE_MODES: dict[int, str]
        :type PRINT_MODES: dict[int, str]

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

    def __init__(self, raw_filename):
        self.raw_filename = raw_filename
        self.raw_data = Path(self.raw_filename).read_bytes()

        self.parsed_values = list()
        self.parsed_timestamps = list()
        self.print_mode = None
        self.rate_mode = None

    def parse(self):
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
                print("Partial data => reject")
                return

        for databyte in it_raw_data:
            if databyte == 0x1B:
                escmode = True
                continue

            # Extract the header; ESC 0
            if escmode and databyte == ord("0"):
                print("SEIKO header probe")
                data = read_from_buffer(1)
                if data is None:
                    return
                self.rate_mode = data[0]
                print("rate:", self.get_rate_mode())

            # Begin to extract values only; ESC 1
            if escmode and databyte == ord("1"):
                print("PROBE ESC 1 found")
                seiko_mode = True
                continue

            # Begin to extract timestamps + values; ESC T
            if escmode and databyte == ord("T"):
                print("Timestamp found")
                timestamp_mode = True

                # Consume the timestamp + the ESC 1 header that follows
                # the next iteration will be at the same point as if there had
                # been no timestamp: mode byte
                data = read_from_buffer(5)
                if data is None:
                    return

                data = unpack(">BBBH", data)
                hours, minutes, seconds, esc1_header = data
                assert esc1_header == 0x1B31

                print("> timestamp: ", hours, minutes, seconds)
                self.parsed_timestamps.append(
                    ":".join(map(lambda val: format(val, "#02"), (minutes, seconds)))
                )
                continue

            # Extract values
            if escmode and (seiko_mode or timestamp_mode):
                print_mode = databyte
                assert print_mode in (0, 1, 2, 3), f"Unknown mode {print_mode}"
                self.print_mode = print_mode
                print("Reading", self.get_print_mode())

                data = read_from_buffer(2)
                if data is None:
                    return

                data = unpack("BB", data)
                byte3, ukn_flag = data

                sign = -1 if byte3 & 1 else 1
                # 1st bit is the sign flag
                # if sign == -1:
                #     print("negative value")

                if byte3 & 128 == 128:  # 0x80
                    sign_chr = "+" if sign else "-"
                    print("Scale ERROR", sign_chr)
                    # => no value, Skip value
                    # self.parsed_values.append(f"{sign_chr} OUT OF RANGE")
                    self.parsed_values.append(None)
                    continue

                # Remove the sign flag, and get the gat mode in use
                gate_mode = byte3 & ~1
                print("gate mode (raw)", gate_mode, ": ", end="")
                if gate_mode == 0:
                    print("seconds")
                elif gate_mode & 32 == 32:  # 0x20
                    print("Hz")
                else:
                    print("ukn error ??")
                    raise Exception

                if gate_mode & 16 == 16:  # 0x10 flag, in 0x30 with 0x20 gate mode
                    print("1st val of Hz mode ?")

                data = read_from_buffer(3)
                if data is None:
                    return

                # values:
                # ?? val1, val2, val3
                sign = -1 if byte3 & 1 else 1
                measure = int(hexlify(data)) / 1000 * sign
                print(">", measure)

                self.parsed_values.append(measure)

            escmode = False
            seiko_mode = False
            timestamp_mode = False

    def get_rate_mode(self):
        """Get the current rate mode of the file

        See :meth:`RATE_MODES`.
        """
        return SeikoQT2100Parser.RATE_MODES[self.rate_mode]

    def get_print_mode(self):
        """Get the last print mode seen in the values

        Should be the same for all the dataset...

        See :meth:`PRINT_MODES`.
        """
        return SeikoQT2100Parser.PRINT_MODES[self.print_mode]

    def to_csv(self, output_dir="."):
        """Produce a CSV file based on the parsed values

        Erroneous values are displayed in the format ``"sign OUT OF RANGE"``,
        where ``sign`` can be +/- according to the sign of the last correct
        data seen.

        Timestamps are added if they are contained in the file.
        See :meth:`SeikoQT2100Parser`.
        """
        # Format erroneous data
        formatted_values = list()
        sign_chr = "+"
        for index, val in enumerate(self.parsed_values):
            if val is None:
                # Use the sign of the last correct value
                val = f"{sign_chr} OUT OF RANGE"
            else:
                sign_chr = "+" if val > 0 else "-"
            formatted_values.append(val)

        # Build CSV header & rows according to the presence of timestamps
        header = [self.get_rate()]
        if self.parsed_timestamps:
            # File is timestamped by Retroprinter
            header = ["Time Stamp"] + header
            rows = zip(self.parsed_timestamps, formatted_values)
        else:
            # Raw file from the timegrapher
            rows = ((val,) for val in formatted_values)

        # Dump to CSV
        with open(Path(output_dir) / "my_qt2100.csv", "w", newline="") as csvfile:
            seiko_writer = csv.writer(csvfile)
            seiko_writer.writerow(header)
            seiko_writer.writerows(rows)

    def to_graph(self, output_dir=".", debug=True):
        """
        Mode 1B:
            no accumulated values: just 1 trace centered on vertical axis around 0

        Mode A (10S, 2M):
            accumulated rates

        Mode C:
            "%s RATE + %d%d.%d%d%d SEC/DAY",timeStampString,digit2,digit3,digit4,digit5,digit6

        """
        if self.print_mode in (1, 2):
            self.build_graph_mode_a(output_dir=output_dir, debug=debug)
        else:
            self.build_graph_mode_b(output_dir=output_dir, debug=debug)

    def build_graph_mode_b(self, output_dir=".", debug=False):
        # Handle erronerous values during measurement
        mean_rate = stat.mean(val for val in self.parsed_values if val)
        formatted_values = []
        erroneous_indexes = []
        for index, val in enumerate(self.parsed_values):
            # Replace erroneous measure by tick or tock respective average
            if val is None:
                formatted_values.append(mean_rate)
                erroneous_indexes.append(index)
                continue

            formatted_values.append(val)

        # Build colors & highlight erroneous values in red
        colors = [
            "#d62728" if idx in erroneous_indexes else "#1f77b4"
            for idx in range(len(formatted_values))
        ]

        serie = pd.DataFrame(
            {"xticks": list(range(len(formatted_values))), "values": formatted_values}
        )
        print(serie.describe())
        ax = serie.plot.line(style="-", y="values")
        serie.plot.scatter(
            x="xticks",
            y="values",
            title=f"Mode {self.get_print_mode()} - {self.get_rate().title()}",
            c=colors,
            zorder=2,
            ax=ax,
        )

        # Improve lisibility
        ax.set_xlabel("")
        ax.set_ylabel("Daily Rate (Sec/Day)")
        ax.legend().set_visible(False)  # on supprime la légende

        # Width of x-axis muts be at least 1 day
        y_max = y if (y := max(formatted_values)) > 1.0 else 1.0
        y_min = y if (y := min(formatted_values)) < -1.0 else -1.0
        ax.set_ylim(y_min, y_max)

        plt.minorticks_on()
        plt.tick_params(
            axis="x",  # changes apply to the x-axis
            which="both",  # both major and minor ticks are affected
            bottom=False,  # ticks along the bottom edge are off
            top=False,  # ticks along the top edge are off
            labelbottom=False,  # labels along the bottom edge are off
        )

        ax.yaxis.grid(True, which="minor", linestyle=":")
        ax.yaxis.grid(True, which="major", linestyle="-")

        fig = ax.get_figure()
        fig.savefig(Path(output_dir) / "figure.pdf")

        if debug:
            plt.show()

        # Close previous fig (free memory)
        plt.close(fig)
        assert not plt.get_fignums()

    def build_graph_mode_a(self, output_dir=".", debug=False):
        """

        :About error handling:

        In modern systems we can have the full dataset in memory at a time;
        Replacing the erroneous data with the most neutral values can be made
        can be done using the averages of their respective series.
        This will minimize the effect on the cumulated values.
        Not replacing them will corrupt the graph (unless the data is deleted
        in pairs.

        :param output_dir:
        :param debug:
        :return:
        """

        MEASURES_PER_DAY = 50

        def ref_curve(rate_per_day=10):
            """Generator of values according the given rate per day

            - 1 day is splited into 50 measures by the device

            - 10s/day = 10s for 50 ticks; each tick will be 0.2.
              Drawing a straight line with such a slope will give the following
              serie of points: ``[0, 0.2, 0.4, 0.6, ...]``

            Can be used to draw reference straight line or to generate axis ticks
            of a graph.

            :Example to trace a line with a 600secs/day slope:

            >>> g = ref_curve(rate_per_day=600)
            >>> ref_values = [next(g) for _ in range(30)]
            >>> serie = pd.Series(ref_values)
            >>> serie.plot()
            """
            offset = rate_per_day / MEASURES_PER_DAY
            val = 0
            yield 0
            while True:
                val += offset
                yield val

        def generate_ticks(days_duration=None):
            """Generator of axis ticks

            Divide the X axis unit (1) into 50 values (1 day):
            25 values for each tick and tock: 1 axis tick every 0.02.

            :keyword days_duration: Values can be reset at regular intervals of days.
                This will allow wrapping of values instead of an infinite
                growing of the graph on the right direction.
            """
            while True:
                g = ref_curve(rate_per_day=1)
                if days_duration:
                    yield from (
                        next(g) for _ in range(days_duration * MEASURES_PER_DAY)
                    )
                else:
                    yield from g

        # Handle erronerous values during measurement (see docstring)
        # Simulate missing value
        self.parsed_values[50] = None

        ticks = self.parsed_values[0::2]
        tocks = self.parsed_values[1::2]
        ticks_mean = stat.mean(val for val in ticks if val)
        tocks_mean = stat.mean(val for val in tocks if val)

        print(ticks_mean, tocks_mean)
        beat_error = ticks_mean + tocks_mean
        print("beat error", beat_error)

        formatted_values = []
        erroneous_indexes = []
        for index, val in enumerate(self.parsed_values):
            # Replace by previous tic or tac
            # if not isinstance(val, (int, float)):
            #     if index - 2 < 0:
            #         formatted_values = []
            #         continue
            #     formatted_values.append(formatted_values[index -2])
            #     continue

            # Replace erroneous measure by tick or tock respective average
            if val is None:
                formatted_values.append(ticks_mean if index % 2 == 0 else tocks_mean)
                erroneous_indexes.append(index)
                continue

            formatted_values.append(val)

        # Build colors & highlight erroneous values in red
        colors = [
            "#d62728" if idx in erroneous_indexes else "#1f77b4"
            for idx in range(len(formatted_values))
        ]

        # Build values that will be displayed
        cumulated_values = cumsum(formatted_values)

        # Max x-axis duration: the remaining values restart at x-axis 0 (wrap values)
        g = generate_ticks(days_duration=2)
        xticks = [round(next(g), 2) for _ in range(len(formatted_values))]

        df = pd.DataFrame(
            zip(xticks, cumulated_values), columns=["xticks", "cum_values"]
        )
        print(df.describe())

        # Display data
        ax = df.plot.scatter(
            x="xticks",
            y="cum_values",
            title=f"Mode {self.get_print_mode()} - {self.get_rate().title()}",
            c=colors,
        )

        # Improve lisibility
        ax.set_xlabel("Days")
        ax.set_ylabel("Cumulated seconds")

        # Show full grid
        ax.xaxis.grid(True, which="minor", linestyle=":")
        ax.xaxis.grid(True, which="major", linestyle="-")
        ax.yaxis.grid(True, which="minor", linestyle=":")
        ax.yaxis.grid(True, which="major", linestyle="-")

        # Width of x-axis muts be at least 1 day
        x_max = x if (x := max(xticks)) > 1.0 else 1.0
        ax.set_xlim(0, x_max)
        plt.minorticks_on()

        # ax.invert_xaxis()
        # ax.invert_yaxis()

        fig = ax.get_figure()
        fig.savefig(Path(output_dir) / "figure.pdf")

        if debug:
            plt.show()

        # Close previous fig (free memory)
        plt.close(fig)
        assert not plt.get_fignums()


def main():
    obj = SeikoQT2100Parser("./seiko_qt2100_A10S.raw")
    obj.parse()
    obj.to_csv()
    obj.to_graph()
    exit()

    # obj = SeikoQT2100Parser("./seiko_qt2100_A10S_timestamped.raw")
    # obj.parse()
    # obj.to_csv()

    obj = SeikoQT2100Parser("./seiko_qt2100_B1S_1.raw")
    obj.parse()
    obj.to_csv()
    obj.to_graph()

    obj = SeikoQT2100Parser("./seiko_qt2100_B1S_2.raw")
    obj.parse()
    obj.to_csv()
    obj.to_graph()

    obj = SeikoQT2100Parser("./seiko_qt2100_999999.raw")
    obj.parse()
    obj.to_csv()
    obj.to_graph()


if __name__ == "__main__":
    main()
