#!/usr/bin/env bash

# check if parameter is given
if [ -z "$1" ]; then
    echo "$0 <name>"
    exit 1
fi

script=$(readlink -f "$0")
script_dir=$(dirname "$script")

name=$1
source=$(pwd)/source/acts/acts/$name
build=$(pwd)/build/acts/acts/$name
install_base=$(pwd)/install
venv=$(pwd)/venv

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

    echo "" > "$source/.clangd"
    echo "CompileFlags:" >> "$source/.clangd"
    echo "  CompilationDatabase: $build" >> "$source/.clangd"

    echo "" > "$source/activate.sh"
    echo ". ${venv}/bin/activate" >> "$source/activate.sh"
    echo "" >> "$source/activate.sh"
    echo ". $build/this_acts_withdeps.sh" >> "$source/activate.sh"
else
    echo "source directory already exists: $source"
fi

if [[ ! -d "$build" ]]; then
    echo "create build directory: $build"

    # TODO source deps activate.sh
    export CMAKE_PREFIX_PATH="${install_base}/json/3.11.3:${CMAKE_PREFIX_PATH}"
    export CMAKE_PREFIX_PATH="${install_base}/tbb/2021.11.0:${CMAKE_PREFIX_PATH}"
    export CMAKE_PREFIX_PATH="${install_base}/eigen/3.4.0:${CMAKE_PREFIX_PATH}"
    export CMAKE_PREFIX_PATH="${install_base}/root/6.36.04:${CMAKE_PREFIX_PATH}"
    export CMAKE_PREFIX_PATH="${install_base}/geant4/11.3.1:${CMAKE_PREFIX_PATH}"
    export CMAKE_PREFIX_PATH="${install_base}/pythia/8314:${CMAKE_PREFIX_PATH}"
    export CMAKE_PREFIX_PATH="${install_base}/podio/01-03:${CMAKE_PREFIX_PATH}"
    export CMAKE_PREFIX_PATH="${install_base}/edm4hep/00-99-02:${CMAKE_PREFIX_PATH}"
    export CMAKE_PREFIX_PATH="${install_base}/dd4hep/01-32-01:${CMAKE_PREFIX_PATH}"
    export CMAKE_PREFIX_PATH="${install_base}/hepmc3/3.3.1:$CMAKE_PREFIX_PATH"
    export CMAKE_PREFIX_PATH="${install_base}/geomodel/6.15.0:$CMAKE_PREFIX_PATH"
    export CMAKE_PREFIX_PATH="${venv}:$CMAKE_PREFIX_PATH"

    source "${venv}/bin/activate"

    cmake -S "$source" -B "$build" \
        -GNinja \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
        -DCMAKE_CXX_STANDARD=20 \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
        -DPython_ROOT_DIR="${venv}" \
        -DPython_FIND_VIRTUALENV=ONLY \
        -DACTS_USE_SYSTEM_NLOHMANN_JSON=ON \
        -DACTS_FORCE_ASSERTIONS=ON \
        -DACTS_ENABLE_LOG_FAILURE_THRESHOLD=ON \
        -DACTS_BUILD_EXAMPLES_DD4HEP=ON \
        -DACTS_BUILD_EXAMPLES_GEANT4=ON \
        -DACTS_BUILD_EXAMPLES_PYTHIA8=ON \
        -DACTS_BUILD_EXAMPLES_PYTHON_BINDINGS=ON \
        -DACTS_BUILD_EXAMPLES_PODIO=ON \
        -DACTS_BUILD_EXAMPLES_EDM4HEP=ON \
        -DACTS_BUILD_EXAMPLES_HEPMC3=ON \
        -DACTS_BUILD_PLUGIN_GEOMODEL=ON \
        -DACTS_BUILD_FATRAS=ON \
        -DACTS_BUILD_FATRAS_GEANT4=ON \
        -DACTS_BUILD_ODD=ON \
        -DACTS_BUILD_BENCHMARKS=ON \
        -DACTS_BUILD_UNITTESTS=ON \
        -DACTS_BUILD_INTEGRATIONTESTS=ON \
        -DACTS_BUILD_EXAMPLES_UNITTESTS=ON
else
    echo "build directory already exists: $build"
fi
