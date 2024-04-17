#!/usr/bin/env bash

# check if parameter is given
if [ -z "$1" ]; then
    echo "$0 <name>"
    exit 1
fi

script=$(readlink -f "$0")
script_dir=$(dirname "$script")

name=$1
source=~/cern/source/acts/acts/$name
build=~/cern/build/acts/acts/$name

if [[ ! -d "$source" ]]; then
    echo "create source directory: $source"

    git clone git@github.com:acts-project/acts.git $source
    cd $source
    git remote rm origin
    git remote add origin git@github.com:andiwand/acts.git
    git remote add upstream git@github.com:acts-project/acts.git
    git fetch --all
    git submodule update --init --recursive

    git maintenance start
else
    echo "source directory already exists: $source"
fi

# TODO the activate script needs to be configured
cp "$script_dir/activate.sh" "$source"

source "$source/activate.sh"

if [[ -d "$build" ]]; then
    echo "create build directory: $build"

    cmake -S "$source" -B "$build" \
        -GNinja \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
        -DACTS_FORCE_ASSERTIONS=ON \
        -DACTS_BUILD_EXAMPLES_DD4HEP=ON \
        -DACTS_BUILD_EXAMPLES_GEANT4=ON \
        -DACTS_BUILD_EXAMPLES_PYTHON_BINDINGS=ON \
        -DACTS_BUILD_FATRAS=ON \
        -DACTS_BUILD_FATRAS_GEANT4=ON \
        -DACTS_BUILD_ODD=ON \
        -DACTS_BUILD_UNITTESTS=ON \
        -DACTS_BUILD_INTEGRATIONTESTS=ON
else
    echo "build directory already exists: $build"
fi
