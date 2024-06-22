[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/ysard/seiko_converter)](https://github.com/ysard/libre-printer/releases/latest/)
[![python docstring coverage](./images/interrogate_badge.svg)](https://interrogate.readthedocs.io/en/latest/)
[![python test coverage](./images/coverage.svg)](https://docs.pytest.org/en/latest/)

# Seiko Qt-2100 converter

Seiko converter is a software allowing to generate graphs based on the raw data 
produced by the Seiko Qt-2100 Timegrapher device. 

## Background

By using an interface like the [Libre Printer](https://github.com/ysard/libre-printer) one, 
which can replace a parallel or serial printer, 
you can obtain data as sent by older devices whose printers have unfortunately broken down.

Sometimes old devices cannot be replaced for cost reasons or simply because there is no justification to do so.
However, they often work in pairs with printers that are no longer manufactured and are often the weak point of
the installation because they are prone to breakdowns and the abandonment of the manufacture of their consumables.

## Purpose
The printer linked to the Seiko Qt-2100 chronograph is one of those rare instruments whose
specifications have either never been published or have long been lost.

The specific aim of this project is to process the print data from this device, making it readable, 
usable and printable again according to current modern standards.

## Features

![](./images/A10S_70s.webp)![](./images/A10S_rp.webp)![](./images/A10S.webp)

*In order from left to right, Print Mode A 10S graphs in 3 eras: the 70's,
actual concurrent project, this project*

### Error corrections

As shown in the image above, dots resulting from measurement error on the
device's side are corrected using the most neutral value possible
(the average of the tick or tock values) and clearly displayed on the figure (red dot).

### Horizontal or vertical layout

Horizontal layout is closer to the rendering of modern timegraphers,
but the readability of an ever-expanding downward graph can be easier.

![](./images/horizontal.webp)

```commandline
$ python -m seiko_converter -i data/seiko_qt2100_A10S.raw -g --horizontal
```

### Optional cutoff

Data can be added indefinitely to such a graph. Controlling value overflow for
long data series is important.
A cutoff value can be chosen automatically on the basis of the data or
specified by the user.

![](./images/vertical_cutoff.webp)![](./images/vertical_cutoff_10.webp)

```commandline
$ python -m seiko_converter -i data/seiko_qt2100_A10S.raw -g --vertical -c
$ python -m seiko_converter -i data/seiko_qt2100_A10S.raw -g --vertical -c 10
```

### CSV Export

For further analysis.

## Usage

```commandline
$ python -m seiko_converter -h
usage: __main__.py [-h] -i INPUT_FILE [-o [OUTPUT_FILENAME]] [--csv] [-g] [--horizontal] [--vertical] [-c [CUTOFF]] [-d] [--version] [-v]

options:
  -h, --help            show this help message and exit
  -i INPUT_FILE, --input_file INPUT_FILE
                        Raw file from device. (default: None)
  -o [OUTPUT_FILENAME], --output_filename [OUTPUT_FILENAME]
                        Generated file name. (default: None)
  --csv                 Extract the parsed values into a CSV file. (default: False)
  -g, --graph           Extract the parsed values into a timegrapher style file. (default: False)
  -d, --debug           Show the matplotlib windows. (default: False)
  --version             show program's version number and exit
  -v, --verbose

Graph options:
  --horizontal          Make a horizontal graph that expand downwards; default is vertical.
  --vertical            Make a vertical graph that expand downwards (default).
  -c [CUTOFF], --cutoff [CUTOFF]
                        Only for Mode A graphs. Allow wrapped display to limit infinite graph expansion on the right
                        direction (x-axis). If set on vertical graph: rate values will be cut; if set on horizontal graph:
                        days will be cut. Set it to True for auto-cut (2 days in horizontal mode), False for disabling the
                        feature, or with a custom value adapted to the chosen mode (limit value or time limit in days).
                        (default: True)
```

## License; Free and Open Source

Seiko converter is released under the AGPL (Affero General Public License).
