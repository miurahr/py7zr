#!/usr/bin/env bash
# post-create setup for py7zr
# Older Python versions are covered by CI; here we only compare
# the default (GIL) build and the free-threaded build of the latest Python.
set -euo pipefail

PY_GIL="${PY_GIL:-3.14}"
PY_FT="${PY_FT:-3.14t}"
# Set WITH_SIBLINGS=1 (and enable "repositories" in devcontainer.json)
# to clone pyppmd / pybcj next to py7zr and install them editable.
WITH_SIBLINGS="${WITH_SIBLINGS:-0}"

# 7z command for manual compatibility checks against the reference implementation
sudo apt-get update
sudo apt-get install -y --no-install-recommends p7zip-full
sudo rm -rf /var/lib/apt/lists/*

python -m pip install --user --upgrade uv tox tox-uv
export PATH="$HOME/.local/bin:$PATH"
uv python install "$PY_GIL" "$PY_FT"

parent="$(dirname "$PWD")"
if [ "$WITH_SIBLINGS" = "1" ]; then
  for dep in pyppmd pybcj; do
    [ -d "$parent/$dep" ] || git clone "https://github.com/miurahr/$dep.git" "$parent/$dep"
  done
fi

# .venv    : GIL build
# .venv-ft : free-threaded build
# (if no cp314t wheels exist for a C dependency, uv builds it from sdist)
for spec in "$PY_GIL:.venv" "$PY_FT:.venv-ft"; do
  py="${spec%%:*}"; venv="${spec##*:}"
  uv venv --python "$py" "$venv"
  if [ "$WITH_SIBLINGS" = "1" ]; then
    for dep in pyppmd pybcj; do
      uv pip install --python "$venv/bin/python" -e "$parent/$dep"
    done
  fi
  uv pip install --python "$venv/bin/python" -e ".[test]" \
    || uv pip install --python "$venv/bin/python" -e . pytest
  uv pip install --python "$venv/bin/python" pytest-run-parallel
done

.venv-ft/bin/python -c "import sys, py7zr; print('py7zr', py7zr.__version__, '; GIL enabled =', sys._is_gil_enabled())"

cat <<'MSG'
------------------------------------------------------------
Ready.
  Tests (GIL):             .venv/bin/pytest
  Tests (free-threaded):   PYTHON_GIL=0 .venv-ft/bin/pytest
  Thread-stress tests:     PYTHON_GIL=0 .venv-ft/bin/pytest --parallel-threads=8
  Which C deps keep GIL?:  .venv-ft/bin/python -W error::RuntimeWarning -c "import py7zr"
  Reference 7z:            7z t some.7z
------------------------------------------------------------
MSG
