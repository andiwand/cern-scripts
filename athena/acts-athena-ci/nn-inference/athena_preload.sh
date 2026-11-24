# Match the Athena executable's allocator and math-library interposition.
# Source only after env.sh, immediately before executing the C++ benchmark.
export LD_PRELOAD="$NN_STUDY_LCG/gperftools/2.18.1/x86_64-el9-gcc15-opt/lib/libtcmalloc_minimal.so:$NN_STUDY_EXTERNALS/lib/libintlc.so.5:$NN_STUDY_EXTERNALS/lib/libimf.so"
