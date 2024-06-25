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
"""Seiko converter entry point"""

# Standard imports
import argparse
from pathlib import Path

# Custom imports
from seiko_converter import __version__
from seiko_converter.qt2100_parser import SeikoQT2100Parser
from seiko_converter.qt2100_converter import SeikoQT2100GraphTool
from seiko_converter import commons as cm


def seiko_converter_entry_point(input_file=None, csv=False, graph=False, **kwargs):
    """Init & call the parser & graph functions"""
    parser = SeikoQT2100Parser(input_file)
    obj = SeikoQT2100GraphTool(parser)
    if csv:
        obj.to_csv(**kwargs)
    if graph:
        obj.to_graph(**kwargs)


def args_to_params(args):
    """Return argparse namespace as a dict {variable name: value}"""
    return dict(vars(args).items())


def str2bool(tristate_val):
    """Cast the given value into bool or numeric value

    :rtype: bool | float
    """
    if isinstance(tristate_val, bool):
        return tristate_val
    if tristate_val.lower() in ("yes", "true", "t", "y", "1"):
        return True
    if tristate_val.lower() in ("no", "false", "f", "n", "0"):
        return False
    return float(tristate_val)


def main():
    """Entry point and argument parser"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "-i", "--input_file", help="Raw file from device.", type=Path, required=True
    )

    parser.add_argument(
        "-o",
        "--output_filename",
        nargs="?",
        help="Generated file name.",
        default=None,
        type=Path,
    )

    parser.add_argument(
        "--csv",
        help="Extract the parsed values into a CSV file.",
        action="store_true",
    )

    parser.add_argument(
        "-g",
        "--graph",
        help="Extract the parsed values into a timegrapher style file.",
        action="store_true",
    )

    graph_group = parser.add_argument_group(title="Graph options")
    graph_group.add_argument(
        "--horizontal",
        help="Make a horizontal graph that expand downwards; default is vertical.",
        dest="vertical",
        action="store_false",
    )
    graph_group.add_argument(
        "--vertical",
        help="Make a vertical graph that expand downwards (default).",
        action="store_true",
    )
    graph_group.add_argument(
        "-c",
        "--cutoff",
        help="""Only for Mode A graphs.
            Allow wrapped display to limit infinite graph expansion on
            the right direction (x-axis).
            If set on vertical graph: rate values will be cut;
            if set on horizontal graph: days will be cut.

            Set it to True for auto-cut (2 days in horizontal mode),
            False to disable the feature, or set a custom value adapted to
            the chosen mode (limit value or time limit in days).""",
        type=str2bool,
        nargs="?",
        const=True,
        default=True,
    )

    parser.add_argument(
        "-d",
        "--debug",
        help="Show the matplotlib windows.",
        action="store_true",
    )

    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
    )

    # Get program args and launch associated command
    args = parser.parse_args()
    params = args_to_params(args)

    # Quick check
    assert params[
        "input_file"
    ].exists(), f"Input file <{params['input_file']}> not found!"

    if params["verbose"]:
        cm.log_level("debug")

    # Do magic
    seiko_converter_entry_point(**params)


if __name__ == "__main__":
    main()
