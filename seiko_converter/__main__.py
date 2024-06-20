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
import sys
import argparse
from pathlib import Path

# Custom imports
from seiko_converter import __version__
from seiko_converter.qt2100_parser import SeikoQT2100Parser
from seiko_converter.qt2100_converter import SeikoQT2100GraphTool


def seiko_converter_entry_point(
    *args, input_file=None, csv=False, graph=False, **kwargs
):
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

    parser.add_argument(
        "-d",
        "--debug",
        nargs="?",
        help="Show the matplotlib windows.",
        default=False,
    )

    parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s " + __version__
    )

    # Get program args and launch associated command
    args = parser.parse_args()
    params = args_to_params(args)

    # Quick check
    assert params[
        "input_file"
    ].exists(), f"Input file <{params['input_file']}> not found!"

    # Do magic
    seiko_converter_entry_point(**params)


if __name__ == "__main__":
    main()
