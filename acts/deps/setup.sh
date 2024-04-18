#!/usr/bin/env bash

set -e

###
# Versions
###
json_version="3.11.3"
tbb_version="2021.11.0"
eigen_version="3.4.0"
root_version="6.30.02"
geant4_version="11.2.1"
pythia8_version="8310"
podio_version="00-17-04"
edm4hep_version="00-10-03"
dd4hep_version="01-27-02"
hepmc3_version="3.2.7"

###
# Resulting URLs
###
json_url="https://github.com/nlohmann/json/releases/download/v${json_version}/json.tar.xz"
tbb_url="https://github.com/oneapi-src/oneTBB/archive/refs/tags/v${tbb_version}.tar.gz"
eigen_url="https://gitlab.com/libeigen/eigen/-/archive/${eigen_version}/eigen-${eigen_version}.tar.gz"
root_url="https://root.cern/download/root_v${root_version}.source.tar.gz"
geant4_url="https://gitlab.cern.ch/geant4/geant4/-/archive/v${geant4_version}/geant4-v${geant4_version}.tar.gz"
pythia8_url="https://pythia.org/download/pythia${pythia8_version:0:2}/pythia${pythia8_version}.tgz"
podio_url="https://github.com/AIDASoft/podio/archive/refs/tags/v${podio_version}.tar.gz"
edm4hep_url="https://github.com/key4hep/EDM4hep/archive/refs/tags/v${edm4hep_version}.tar.gz"
dd4hep_url="https://github.com/AIDASoft/DD4hep/archive/refs/tags/v${dd4hep_version}.tar.gz"
hepmc3_url="https://gitlab.cern.ch/hepmc/HepMC3/-/archive/${hepmc3_version}/HepMC3-${hepmc3_version}.tar.gz"

###
# Options
###
source_tree=~/cern/tmp/source
build_tree=
install_tree=

###
# OS detection
###
os_id=
os_version=
has_cvmfs=

if [[ -d "/cvmfs/sft.cern.ch/lcg/views" ]]; then
    has_cvmfs=true
fi

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    . /etc/os-release

    if [[ "$ID" == "ubuntu" ]]; then
        os_id=ubuntu
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    os_id=macos
fi

if [[ -z "$os_id" ]]; then
    echo "Unsupported System"
    exit 1
fi

###
# Dependencies of the dependencies
###

if [[ "$os_id" == "ubuntu" ]]; then
    sudo apt-get install -y \
        build-essential \
        cmake \
        libboost-all-dev \
        ninja-build
elif [[ "$os_id" == "macos" ]]; then
    brew install \
        boost \
        xerces-c
fi

###
# Download and unpack
###

download_unpack() {
    local source=$1
    local destination=$2

    echo "Downloading ${source}"

    if [[ -d "$destination" ]]; then
        echo "Destination ${destination} already exists. Skipping"
        return
    fi

    local parent=$(dirname "$destination")

    mkdir -p "$parent"
    curl -L -o "${destination}_download" "$source"
    mkdir -p "$destination"
    tar -xf "${destination}_download" -C "$destination" --strip-components=1
    rm "${destination}_download"
}

download_unpack "$json_url" "${source_tree}/json/${json_version}"
download_unpack "$tbb_url" "${source_tree}/tbb/${tbb_version}"
download_unpack "$eigen_url" "${source_tree}/eigen/${eigen_version}"
download_unpack "$root_url" "${source_tree}/root/${root_version}"
download_unpack "$geant4_url" "${source_tree}/geant4/${geant4_version}"
download_unpack "$pythia8_url" "${source_tree}/pythia8/${pythia8_version}"
download_unpack "$podio_url" "${source_tree}/podio/${podio_version}"
download_unpack "$edm4hep_url" "${source_tree}/edm4hep/${edm4hep_version}"
download_unpack "$dd4hep_url" "${source_tree}/dd4hep/${dd4hep_version}"
download_unpack "$hepmc3_url" "${source_tree}/hepmc3/${hepmc3_version}"

###
# Configure, build and install
###

# json
cmake -S "${source_tree}/json/${json_version}" -B "${build_tree}/json/${json_version}" \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_INSTALL_PREFIX="${install_tree}/json/${json_version}" \
  -DJSON_BuildTests=OFF
cmake --build "${build_tree}/json/${json_version}" --target install

# tbb
cmake -S "${source_tree}/tbb/${tbb_version}" -B "${build_tree}/tbb/${tbb_version}" \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_INSTALL_PREFIX="${install_tree}/tbb/${tbb_version}" \
  -DTBB_TEST=OFF
cmake --build "${build_tree}/tbb/${tbb_version}" --target install

# eigen
cmake -S "${source_tree}/eigen/${eigen_version}" -B "${build_tree}/eigen/${eigen_version}" \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_INSTALL_PREFIX="${install_tree}/eigen/${eigen_version}"
cmake --build "${build_tree}/eigen/${eigen_version}" --target install

# root
cmake -S "${source_tree}/root/${root_version}" -B "${build_tree}/root/${root_version}" \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_INSTALL_PREFIX="${install_tree}/root/${root_version}" \
  -Dfail-on-missing=ON \
  -Dgdml=ON \
  -Dx11=ON \
  -Dpyroot=On \
  -Ddataframe=ON \
  -Dmysql=OFF \
  -Doracle=OFF \
  -Dpgsql=OFF \
  -Dsqlite=OFF \
  -Dpythia6=OFF \
  -Dpythia8=OFF \
  -Dfftw3=OFF \
  -Dbuiltin_cfitsio=ON \
  -Dbuiltin_xxhash=ON \
  -Dbuiltin_afterimage=ON \
  -Dbuiltin_openssl=ON \
  -Dbuiltin_ftgl=ON \
  -Dbuiltin_glew=ON \
  -Dbuiltin_gsl=ON \
  -Dbuiltin_gl2ps=ON \
  -Dbuiltin_xrootd=ON \
  -Dbuiltin_pcre=ON \
  -Dbuiltin_lzma=ON \
  -Dbuiltin_zstd=ON \
  -Dbuiltin_lz4=ON \
  -Dgfal=OFF \
  -Ddavix=OFF \
  -Dbuiltin_vdt=ON \
  -Dxrootd=OFF \
  -Dtmva=OFF
cmake --build "${build_tree}/root/${root_version}" --target install

# geant4
cmake -S "${source_tree}/geant4/${geant4_version}" -B "${build_tree}/geant4/${geant4_version}" \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_INSTALL_PREFIX="${install_tree}/geant4/${geant4_version}" \
  -DGEANT4_BUILD_TLS_MODEL=global-dynamic \
  -DGEANT4_INSTALL_DATA=ON \
  -DGEANT4_USE_GDML=ON \
  -DGEANT4_USE_SYSTEM_EXPAT=ON \
  -DGEANT4_USE_SYSTEM_ZLIB=ON
cmake --build "${build_tree}/geant4/${geant4_version}" --target install

# pythia8
cd "${source_tree}/pythia8/${pythia8_version}"
./configure --enable-shared --prefix="${install_tree}/pythia8/${pythia8_version}"
make -j12 install

# podio
export CMAKE_PREFIX_PATH="${install_tree}/root/${root_version}"
cmake -S "${source_tree}/podio/${podio_version}" -B "${build_tree}/podio/${podio_version}" \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_INSTALL_PREFIX="${install_tree}/podio/${podio_version}" \
  -DBUILD_TESTING=OFF \
  -USE_EXTERNAL_CATCH2=OFF
cmake --build "${build_tree}/podio/${podio_version}" --target install

# edm4hep
export CMAKE_PREFIX_PATH="${install_tree}/root/${root_version}:${install_tree}/podio/${podio_version}"
cmake -S "${source_tree}/edm4hep/${edm4hep_version}" -B "${build_tree}/edm4hep/${edm4hep_version}" \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_INSTALL_PREFIX="${install_tree}/edm4hep/${edm4hep_version}" \
  -DBUILD_TESTING=OFF \
  -DUSE_EXTERNAL_CATCH2=OFF
cmake --build "${build_tree}/edm4hep/${edm4hep_version}" --target install

# dd4hep
export CMAKE_PREFIX_PATH="${install_tree}/root/${root_version}:${install_tree}/podio/${podio_version}:${install_tree}/edm4hep/${edm4hep_version}"
cmake -S "${source_tree}/dd4hep/${dd4hep_version}" -B "${build_tree}/dd4hep/${dd4hep_version}" \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_INSTALL_PREFIX="${install_tree}/dd4hep/${dd4hep_version}" \
  -DBUILD_TESTING=OFF \
  -DDD4HEP_BUILD_PACKAGES="DDG4 DDDetectors DDRec UtilityApps" \
  -DDD4HEP_USE_GEANT4=ON \
  -DDD4HEP_USE_XERCESC=ON \
  -DDD4HEP_USE_EDM4HEP=ON
cmake --build "${build_tree}/dd4hep/${dd4hep_version}" --target install

# hepmc3
cmake -S "${source_tree}/hepmc3/${hepmc3_version}" -B "${build_tree}/hepmc3/${hepmc3_version}" \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_INSTALL_PREFIX="${install_tree}/hepmc3/${hepmc3_version}" \
  -DHEPMC3_BUILD_STATIC_LIBS=OFF \
  -DHEPMC3_ENABLE_PYTHON=OFF \
  -DHEPMC3_ENABLE_ROOTIO=OFF \
  -DHEPMC3_ENABLE_SEARCH=OFF
cmake --build "${build_tree}/hepmc3/${hepmc3_version}" --target install
