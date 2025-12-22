# VeloSim Documentation

This directory contains the Sphinx documentation for VeloSim.

## Building the Documentation

1. Install documentation dependencies:

```bash
pip install -e ".[docs]"
```

2. Build the HTML documentation:

```bash
cd docs
sphinx-build -b html . _build/html
```

3. View the documentation:
   Open `docs/_build/html/index.html` in your browser.

## Quick Build Script

You can also use the provided script:

```bash
# From the project root
python scripts/build_docs.py
```

## Documentation Structure

- `conf.py` - Sphinx configuration
- `index.rst` - Main documentation page
- `backend.rst` - Backend API documentation
- `simulation.rst` - Simulation engine documentation
- `_build/` - Generated HTML output (gitignored)

## Updating Documentation

The documentation is automatically generated from docstrings in the code. To update:

1. Update docstrings in the source code following Google-style format
2. Rebuild the documentation using the command above
3. The HTML will be regenerated with your changes
