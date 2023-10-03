<div align="center">

# Project {{ cookiecutter.project_name }}

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/Cinnamon/kotaemon)

</div>

# Install

```bash
# Create new conda env (optional)
conda create -n {{ cookiecutter.project_name }} python=3.10
conda activate {{ cookiecutter.project_name }}

# Clone and install the project
git clone "<{{ cookiecutter.project_name }}-repo>"
cd "<{{ cookiecutter.project_name }}-repo>"
pip install -e .

# Generate the project structure
cd ..
kh start-project
```

# Usage

- Build the pipeline in `pipeline.py`

For supported utilities and tools, refer: https://github.com/Cinnamon/kotaemon/wiki/Utilities

# Contribute

- For project issues and errors, please report in this repo issues.
- For kotaemon issues and errors, please report or make PR fixes in https://github.com/Cinnamon/kotaemon.git
- If the template for this project has issues and errors, please report or make
  PR fixes in https://github.com/Cinnamon/kotaemon/tree/main/templates/project-default
