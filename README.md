# LayerLog

A tiny, dependency-free command-line logbook for 3D prints. Record what you printed, which printer and material you used, and how much filament and time it took.

## Requirements

- Python 3.10 or newer
- No third-party runtime dependencies

## Install

From this repository:

```console
python -m pip install .
```

For development, install the project in editable mode:

```console
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Usage

Record a completed print:

```console
layerlog add --name "Benchy" --printer "Bambu A1" --material PLA --grams 18 --minutes 13
```

List recent prints:

```console
layerlog list
layerlog list --limit 5
```

Show totals and breakdowns:

```console
layerlog stats
```

Add a note to an entry:

```console
layerlog add --name "Desk organiser" --printer "Ender-3 V3 SE" --material PETG --grams 86 --minutes 145 --notes "Printed in two parts"
```

By default, entries are stored locally in:

- Windows: `%APPDATA%\LayerLog\prints.json`
- macOS: `~/Library/Application Support/LayerLog/prints.json`
- Linux: `$XDG_DATA_HOME/layerlog/prints.json` (or `~/.local/share/layerlog/prints.json`)

Pass `--db PATH` before the subcommand to use another file:

```console
layerlog --db ./my-prints.json add --name "Calibration cube" --printer "Printer 1" --grams 4 --minutes 12
layerlog --db ./my-prints.json stats
```

LayerLog only stores the information you enter. It does not connect to printers or upload your print history.

## License

MIT. See [LICENSE](LICENSE).
