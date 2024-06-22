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
from functools import partial
from math import ceil, floor

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
        formatted_values = []
        sign_chr = "+"
        for val in self.parsed_values:
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
        with open(filename, "w", newline="", encoding="utf8") as csvfile:
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

    def build_graph_mode_b(
        self, output_filename=None, vertical=True, debug=False, **kwargs
    ):
        """Build graph for data generated in print mode B 1S

        For Quartz watch (LCD or stepper).
        No accumulated values: just 1 "vertical" line for sec/day rate.

        :key output_filename: Output filepath for the graph file
            (By default it will be a pdf based on the input filename,
            but that can be changed by specifying another extension). (default: None)
        :key vertical: Build a vertical graph that expands downwards, instead of
            a horizontal graph that expands to the right.
        :key debug: (Optional) Show the graph in matplotlib window. (default: False)
        :type output_filename: str
        :type vertical: bool
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
            {
                "axisticks": list(range(len(formatted_values))),
                "values": formatted_values,
            }
        )
        LOGGER.info(serie["values"].describe())

        # Plot (swap axis for vertical graph)
        if vertical:
            ax = serie.plot.line(style="-", x="values")
            scatter_plot_func = partial(serie.plot.scatter, x="values", y="axisticks")
            legend = "⊖↙ ↘⊕"
        else:
            ax = serie.plot.line(style="-", y="values")
            scatter_plot_func = partial(serie.plot.scatter, x="axisticks", y="values")
            legend = "↗+ ↘-"

        scatter_plot_func(
            title=f"Mode {self.print_mode} - {self.rate_mode.title()} - {legend}",
            c=colors,
            zorder=2,
            ax=ax,
        )

        # Improve lisibility
        # Legend
        if vertical:
            ax.set_xlabel("Daily Rate (Sec/Day)")
            ax.set_ylabel("")
        else:
            ax.set_xlabel("")
            ax.set_ylabel("Daily Rate (Sec/Day)")
        ax.legend().set_visible(False)  # 1 serie of data: delete legend

        # Width of x-axis muts be at least 1 day
        axis_max = max_val if (max_val := ceil(max(formatted_values))) > 1.0 else 1.0
        axis_min = min_val if (min_val := floor(min(formatted_values))) < -1.0 else -1.0
        axis_lim_func = ax.set_xlim if vertical else ax.set_ylim
        axis_lim_func(axis_min, axis_max)

        # Ticks & grid
        plt.minorticks_on()
        if vertical:
            # Remove ticks info on y-axis, grid must be on x-axis only
            axis_grid_func = ax.xaxis.grid
            ax.invert_yaxis()  # The graph expands downwards
            plt.tick_params(
                axis="y",  # changes apply to the x-axis
                which="both",  # both major and minor ticks are affected
                left=False,  # ticks along the bottom edge are off
                right=False,  # ticks along the top edge are off
                labelleft=False,  # labels along the bottom edge are off
            )
        else:
            # Remove ticks info on x-axis, grid must be on y-axis only
            axis_grid_func = ax.yaxis.grid
            plt.tick_params(
                axis="x",  # changes apply to the x-axis
                which="both",  # both major and minor ticks are affected
                bottom=False,  # ticks along the bottom edge are off
                top=False,  # ticks along the top edge are off
                labelbottom=False,  # labels along the bottom edge are off
            )

        axis_grid_func(True, which="minor", linestyle=":")
        axis_grid_func(True, which="major", linestyle="-")

        # Export the graph
        if debug:
            plt.show()

        # Export the graph
        fig = ax.get_figure()
        self.save_fig(fig, output_filename)

    @staticmethod
    def build_wrapped_dataset(values, cut_val):
        """Build wrapped values according the given cutoff value

        The aim is to reposition all data above a certain value on the right-hand
        side of the graph to the left-hand side of the graph until it reaches
        the right-hand edge again, and so on.

        We handle negative & positive slopes.
        """
        temp_values = []
        for val in values:
            abs_val = abs(val)
            if abs_val > cut_val:
                sign = 1 if val > 0 else -1
                dividend = abs_val // cut_val
                val = abs_val % cut_val
                if sign > 0:
                    # val += min(values) + (dividend - 1) * cut_val
                    val += -cut_val + (dividend - 1) * cut_val
                    val *= sign
                else:
                    val *= -1
                    # val += max(values) - (dividend - 1) * cut_val
                    val += cut_val - (dividend - 1) * cut_val
            temp_values.append(val)
        return temp_values

    def build_graph_mode_a(
        self, output_filename=None, vertical=True, cutoff=True, debug=False, **kwargs
    ):
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

        :key output_filename: Output filepath for the graph file
            (By default it will be a pdf based on the input filename,
            but that can be changed by specifying another extension). (default: None)
        :key vertical: If True a vertical graph will be made. The graph will
            always expand downwards. This representation is similar to the one used
            for the QT-2100 device.
            Otherwise, the graph will expand on the right direction. This is
            a representation used on modern timegraphers.
            (default: True)
        :key cutoff: Allow wrapped display to limit infinite graph expansion on
            the right direction (x-axis).
            If set on vertical graph: rate values will be cut;
            if set on horizontal graph: days will be cut.

            Set it to True for auto-cut (2 days in horizontal mode),
            False for disabling the feature, or with a custom value adapted to
            the chosen mode (limit value or time limit in days).
            (default: True)
        :key debug: (Optional) Show the graph in matplotlib window. (default: False)
        :type vertical: bool
        :type cutoff: bool | int | float
        :type output_filename: str
        :type debug: bool
        """
        measures_per_day = 50

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
            offset = rate_per_day / measures_per_day
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
                        next(g) for _ in range(int(days_duration) * measures_per_day)
                    )
                else:
                    yield from g

        # Handle erronerous values during measurement (see docstring)
        # Simulate missing value
        # self.parsed_values[0] = None
        # self.parsed_values[50] = None
        # self.parsed_values[-1] = None

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

        # Simulate opposite rate
        # cumulated_values = [-1 * val for val in cumulated_values]

        # Max x-axis: the remaining values restart at x-axis 0 (wrap values)
        if not vertical and cutoff is True:
            # Horizontal mode, auto cutoff asked: 2 days
            cutoff = 2
        # Cut data only on vertical mode, on days otherwise
        days_duration = None if vertical else cutoff
        g = generate_ticks(days_duration=days_duration)
        dayticks = [round(next(g), 2) for _ in range(len(formatted_values))]

        if vertical:
            # Vertical mode: cutoff is made on data
            if not isinstance(cutoff, bool):
                # Use the given value no matter what
                cut_val = float(cutoff)
            elif cutoff:
                # Take the 1st value, that can be positive or negative; it gives
                # a good info about the dataset shape (big or small values for high
                # or small rates)
                cut_val = ceil(abs(cumulated_values[0]))

            if cutoff:
                # Cutoff behavior is set: wrap the dataset
                cumulated_values = self.build_wrapped_dataset(cumulated_values, cut_val)

        df = pd.DataFrame(
            zip(dayticks, cumulated_values), columns=["dayticks", "cum_values"]
        )
        LOGGER.info(df["cum_values"].describe())

        # Plot (swap axis for vertical graph)
        if vertical:
            scatter_plot_func = partial(df.plot.scatter, x="cum_values", y="dayticks")
        else:
            scatter_plot_func = partial(df.plot.scatter, x="dayticks", y="cum_values")

        ax = scatter_plot_func(
            title=f"Mode {self.print_mode}",  # - {self.rate_mode.title()}",
            c=colors,
            zorder=2,  # Grid under the data
        )

        # Improve lisibility
        # Show full grid
        ax.xaxis.grid(True, which="minor", linestyle=":")
        ax.xaxis.grid(True, which="major", linestyle="-")
        ax.yaxis.grid(True, which="minor", linestyle=":")
        ax.yaxis.grid(True, which="major", linestyle="-")

        plt.minorticks_on()
        fig = ax.get_figure()

        if vertical:
            # ax.invert_xaxis()  # Similar to seiko QT-2100 but less clear (?)
            ax.invert_yaxis()

            # Legend
            ax.set_xlabel("Cumulated seconds")
            ax.set_ylabel("Days")

            # x-axis limits
            if not isinstance(cutoff, bool):
                lim = ceil(cut_val)
                ax.set_xlim(-lim, lim)

            # Reshape the graph (taller than wide), depending on days
            fig.set_figheight(4.2 * len(cumulated_values) // measures_per_day)

            current_ticks_values = ax.get_xticks()
        else:
            # Legend
            ax.set_xlabel("Days")
            ax.set_ylabel("Cumulated seconds")

            # Width of x-axis muts be at least 1 day
            if max(dayticks) < 1.0:
                ax.set_xlim(xmax=1.0)

            current_ticks_values = ax.get_yticks()

        # Search the current rate given by the difference between 2 major ticks
        # and show it in title
        current_rate = current_ticks_values[-1] - current_ticks_values[-2]
        unit = "Secs" if current_rate > 1 else "Sec"
        ax.set_title(ax.get_title() + f" - {current_rate} {unit}/Day")

        # Export the graph
        if debug:
            plt.show()

        self.save_fig(fig, output_filename)

    def save_fig(self, fig, output_filename):
        """Export the graph

        :param fig: Matplotlib figure
        :param output_filename: If None, the name will be based on the original
            one and a pdf will be generated.
        :type fig: matplotlib.figure.Figure
        :type output_filename: None or str
        """
        filename = output_filename or self.get_output_filename(".pdf")
        fig.savefig(filename)

        # Last reshape
        plt.tight_layout()

        # Close the fig (free memory)
        plt.close(fig)
        # WARNING: When the fig is plotted (debug mode), tight_layout() call is
        # not compatible with close()... An exception will be raised
        assert not plt.get_fignums(), plt.get_fignums()
