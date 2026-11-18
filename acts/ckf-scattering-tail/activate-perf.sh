# environment for the proto-ckf-scattering-tail-perf build (worktree ckf-tail)
. ~/cern/source/spack/share/spack/setup-env.sh
spack env activate ~/cern/source/acts/ci-dependencies
. ~/cern/source/acts/ci-dependencies/.python-env/bin/activate
. ~/cern/build/acts/acts/ckf-tail/this_acts_withdeps.sh
export PYTHONPATH=~/cern/source/acts/acts/ckf-tail/Examples/Scripts/Python:$PYTHONPATH
export ACTS_SOURCE=~/cern/source/acts/acts/ckf-tail
