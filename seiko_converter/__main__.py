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
import argparse
from seiko_converter.qt2100_parser import SeikoQT2100Parser
from seiko_converter.qt2100_converter import SeikoQT2100GraphTool


def main():
    parser = SeikoQT2100Parser("./data/seiko_qt2100_A10S.raw")
    obj = SeikoQT2100GraphTool(parser)
    obj.to_csv()
    obj.to_graph()

    parser = SeikoQT2100Parser("./data/seiko_qt2100_B1S_1.raw")
    obj = SeikoQT2100GraphTool(parser)
    obj.to_csv()
    obj.to_graph()


if __name__ == "__main__":
    main()
