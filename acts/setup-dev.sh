#!/bin/zsh

# check if parameter is given
if [ -z "$1" ]; then
    echo "$0 <name>"
    exit 1
fi

name=$1
source=~/cern/source/acts/acts/$name
build=~/cern/build/acts/acts/$name
script=$(readlink -f "$0")
script_dir=$(dirname "$script")

# check if directory exists
if [[ -d "$source" || -d "$build" ]]; then
    echo "directory $source already exists"
    exit 1
fi

git clone git@github.com:acts-project/acts.git $source
cd $source
git remote rm origin
git remote add origin git@github.com:andiwand/acts.git
git remote add upstream git@github.com:acts-project/acts.git
git fetch
git submodule update --init --recursive

cmake -S "$source" -B "$build" \
  -GNinja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
  -DACTS_FORCE_ASSERTIONS=ON

cp "$script_dir/activate.sh" "$source"
