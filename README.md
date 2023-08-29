# kotaemon

Quick and easy AI components to build Kotaemon - applicable in client
project.

## Install

```shell
pip install kotaemon@git+ssh://git@github.com/Cinnamon/kotaemon.git
```

## Contribute

### Setup

```shell
# Create conda environment (suggest 3.10)
conda create -n kotaemon python=3.10
conda activate kotaemon

# Install all
pip install -e ".[dev]"

# Test
pytest tests
```

### Code base structure

- documents: define document
- loaders
