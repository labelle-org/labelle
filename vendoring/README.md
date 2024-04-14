# Vendored dependencies

This directory contains vendored dependencies managed by the
[`vendoring`](https://github.com/pradyunsg/vendoring) tool.

## Updating dependencies

To update the vendored dependencies, run:

```bash
vendoring update
```

## Packages vendored

### [`matplotlib`](https://github.com/matplotlib/matplotlib/)

We take just a subset of `font_manager.py` used for selecting fonts. See
[LICENSE](../src/labelle/_vendor/matplotlib/LICENSE) for the license.
