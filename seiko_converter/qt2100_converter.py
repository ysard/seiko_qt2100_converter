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
"""Graphical functions used to analyze parsed data, grouped in SeikoQT2100GraphTool class"""

# Standard imports
from pathlib import Path
import csv
import statistics as stat

# Custom imports
import pandas as pd
import matplotlib.pyplot as plt
from numpy import cumsum

from seiko_converter.qt2100_parser import SeikoQT2100Parser
import seiko_converter.commons as cm

LOGGER = cm.logger()


class SeikoQT2100GraphTool:
    """Graph & CSV builder using the SeikoQT2100Parser parser on the files
    produced by the Seiko QT-2100 Timegrapher device
    """

    # Graph colors
    RED = "#d62728"
    BLUE = "#1f77b4"

    def __init__(self, parser: SeikoQT2100Parser):
        """Constructor

        :param parser: Expect an initialised parser object on a printer file.
        """
        self.parser = parser
        self.parser.parse()

    @property
    def parsed_values(self):
        """Get parsed values from the parser"""
        return self.parser.parsed_values

    @property
    def parsed_timestamps(self):
        """Get parsed timestamps from the parser (can be empty)"""
        return self.parser.parsed_timestamps

    @property
    def rate_mode(self):
        """Get sec/day rate from the parser"""
        return self.parser.get_rate_mode()

    @property
    def print_mode(self):
        """Get print mode from the parser"""
        return self.parser.get_print_mode()

    def get_output_filename(self, suffix=""):
        """Get filename based on the original parsed filename and the given suffix

        :param suffix: dotted filename suffix
        :type suffix: str
        """
        filename = Path(self.parser.raw_filename)
        return Path(filename.stem).with_suffix(suffix)

    def to_csv(self, output_filename=None, **kwargs):
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
        header = [self.rate_mode]
        if self.parsed_timestamps:
            # File is timestamped by Retroprinter
            header = ["Time Stamp"] + header
            rows = zip(self.parsed_timestamps, formatted_values)
        else:
            # Raw file from the timegrapher
            rows = ((val,) for val in formatted_values)

        # Dump to CSV
        filename = output_filename or self.get_output_filename(".csv")
        with open(filename, "w", newline="") as csvfile:
            seiko_writer = csv.writer(csvfile)
            seiko_writer.writerow(header)
            seiko_writer.writerows(rows)

    def to_graph(self, *args, **kwargs):
        """Build and export a graph according to the print modes of the parsed data

        Mode B 1S:
            For Quartz watch (LCD or stepper).
            No accumulated values: just 1 "vertical" line for sec/day rate.

        Mode A (10S, 2M):
            For mechanical watch; Timegrapher style plot of the accumulated rates.

        Mode C:
            For Quartz watch (LCD or stepper).
            Same data used by the graphical mode B 1S.
            => not implemented, you should use :meth`to_csv` method for this one.
        """
        if self.print_mode in ("A 10S", "A 2M"):
            self.build_graph_mode_a(*args, **kwargs)
        elif self.print_mode == "B 1S":
            self.build_graph_mode_b(*args, **kwargs)
        else:
            raise NotImplementedError(
                "For this mode, you should use to_csv() method instead"
            )

    def build_graph_mode_b(self, output_filename=None, debug=False, **kwargs):
        """Build graph for data generated in print mode B 1S

        For Quartz watch (LCD or stepper).
        No accumulated values: just 1 "vertical" line for sec/day rate.

        :param output_filename: Output filepath for the pdf file.
        :key debug: (Optional) Show the graph in matplotlib window. (default: False)
        :type output_filename: str
        :type debug: bool
        """
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
            self.RED if idx in erroneous_indexes else self.BLUE
            for idx in range(len(formatted_values))
        ]

        serie = pd.DataFrame(
            {"xticks": list(range(len(formatted_values))), "values": formatted_values}
        )
        LOGGER.info(serie["values"].describe())

        ax = serie.plot.line(style="-", y="values")
        serie.plot.scatter(
            x="xticks",
            y="values",
            title=f"Mode {self.print_mode} - {self.rate_mode.title()}",
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

        # Export the graph
        fig = ax.get_figure()
        filename = output_filename or self.get_output_filename(".pdf")
        fig.savefig(filename)

        if debug:
            plt.show()

        # Close previous fig (free memory)
        plt.close(fig)
        assert not plt.get_fignums()

    def build_graph_mode_a(self, output_filename=None, debug=False, **kwargs):
        """Build graph for data generated in print mode A 1S/2M

        For mechanical watch; Timegrapher style plot of the accumulated rates.

        There are always 50 measures per day (25 values for each tick and tock).

        :About error handling:

        In modern systems we can have the full dataset in memory at a time;
        Replacing the erroneous data with the most neutral values can be made
        can be done using the averages of their respective series.
        This will minimize the effect on the cumulated values.
        Not replacing them will corrupt the graph (unless the data is deleted
        in pairs.

        :param output_filename: Output filepath for the pdf file.
        :key debug: (Optional) Show the graph in matplotlib window. (default: False)
        :type output_filename: str
        :type debug: bool
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

        LOGGER.debug(
            "Calculated averages, ticks: %s, tocks: %s", ticks_mean, tocks_mean
        )
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
            self.RED if idx in erroneous_indexes else self.BLUE
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
        LOGGER.info(df["cum_values"].describe())

        # Display data
        ax = df.plot.scatter(
            x="xticks",
            y="cum_values",
            title=f"Mode {self.print_mode} - {self.rate_mode.title()}",
            c=colors,
            zorder=2,
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

        # Export the graph
        fig = ax.get_figure()
        filename = output_filename or self.get_output_filename(".pdf")
        fig.savefig(filename)

        if debug:
            plt.show()

        # Close previous fig (free memory)
        plt.close(fig)
        assert not plt.get_fignums()
