source ~/cern/venv/bin/activate

export Python_ROOT_DIR="~/cern/venv"
export Python_FIND_VIRTUALENV=ONLY

###

cmake -S ~/cern/source/json/3.11.3 -B ~/cern/build/json/3.11.3 \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=20 \
  -DCMAKE_INSTALL_PREFIX=~/cern/install/json/3.11.3 \
  -DJSON_BuildTests=OFF
cmake --build ~/cern/build/json/3.11.3 --target install

export CMAKE_PREFIX_PATH="~/cern/install/json/3.11.3:$CMAKE_PREFIX_PATH"

###

cmake -S ~/cern/source/tbb/2021.11.0 -B ~/cern/build/tbb/2021.11.0 \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=20 \
  -DCMAKE_INSTALL_PREFIX=~/cern/install/tbb/2021.11.0 \
  -DTBB_TEST=OFF
cmake --build ~/cern/build/tbb/2021.11.0 --target install

export CMAKE_PREFIX_PATH="~/cern/install/tbb/2021.11.0:$CMAKE_PREFIX_PATH"

###

cmake -S ~/cern/source/eigen/3.4.0 -B ~/cern/build/eigen/3.4.0 \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=20 \
  -DCMAKE_INSTALL_PREFIX=~/cern/install/eigen/3.4.0
cmake --build ~/cern/build/eigen/3.4.0 --target install

export CMAKE_PREFIX_PATH="~/cern/install/eigen/3.4.0:$CMAKE_PREFIX_PATH"

###

cmake -S ~/cern/source/root/6.34.08 -B ~/cern/build/root/6.34.08 \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=20 \
  -DCMAKE_INSTALL_PREFIX=~/cern/install/root/6.34.08 \
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
cmake --build ~/cern/build/root/6.34.08 --target install

export CMAKE_PREFIX_PATH="~/cern/install/root/6.34.08:$CMAKE_PREFIX_PATH"

###

brew install xerces-c

cmake -S ~/cern/source/geant4/11.3.1 -B ~/cern/build/geant4/11.3.1 \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=20 \
  -DCMAKE_INSTALL_PREFIX=~/cern/install/geant4/11.3.1 \
  -DGEANT4_BUILD_TLS_MODEL=global-dynamic \
  -DGEANT4_INSTALL_DATA=ON \
  -DGEANT4_USE_GDML=ON \
  -DGEANT4_USE_SYSTEM_EXPAT=ON \
  -DGEANT4_USE_SYSTEM_ZLIB=ON
cmake --build ~/cern/build/geant4/11.3.1 --target install

export CMAKE_PREFIX_PATH="~/cern/install/geant4/11.3.1:$CMAKE_PREFIX_PATH"

###

cmake -S ~/cern/source/geomodel/6.15.0 -B ~/cern/build/geomodel/6.15.0 \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=20 \
  -DCMAKE_INSTALL_PREFIX=~/cern/install/geomodel/6.15.0 \
  -DGEOMODEL_BUILD_GEOMODELG4=ON
cmake --build ~/cern/build/geomodel/6.15.0 --target install

export CMAKE_PREFIX_PATH="~/cern/install/geomodel/6.15.0:$CMAKE_PREFIX_PATH"

###

cd ~/cern/source/pythia/8314
CXX=clang++ \
./configure \
  --prefix=~/cern/install/pythia/8314 \
  --cxx=clang++ \
  --cxx-common="-O2 -std=c++20 -fPIC -pthread" # -pedantic -W -Wall -Wshadow 
make -j12 install

export CMAKE_PREFIX_PATH="~/cern/install/pythia/8314:$CMAKE_PREFIX_PATH"

###

cmake -S ~/cern/source/podio/01-03 -B ~/cern/build/podio/01-03 \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=20 \
  -DCMAKE_INSTALL_PREFIX=~/cern/install/podio/01-03 \
  -DBUILD_TESTING=OFF \
  -DUSE_EXTERNAL_CATCH2=OFF
cmake --build ~/cern/build/podio/01-03 --target install

export CMAKE_PREFIX_PATH="~/cern/install/podio/01-03:$CMAKE_PREFIX_PATH"

###

cmake -S ~/cern/source/edm4hep/00-99-02 -B ~/cern/build/edm4hep/00-99-02 \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=20 \
  -DCMAKE_INSTALL_PREFIX=~/cern/install/edm4hep/00-99-02 \
  -DBUILD_TESTING=OFF \
  -DUSE_EXTERNAL_CATCH2=OFF
cmake --build ~/cern/build/edm4hep/00-99-02 --target install

export CMAKE_PREFIX_PATH="~/cern/install/edm4hep/00-99-02:$CMAKE_PREFIX_PATH"

###

brew install boost

cmake -S ~/cern/source/dd4hep/01-31 -B ~/cern/build/dd4hep/01-31 \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=20 \
  -DCMAKE_INSTALL_PREFIX=~/cern/install/dd4hep/01-31 \
  -DBUILD_DOCS=OFF \
  -DBUILD_TESTING=OFF \
  -DDD4HEP_BUILD_PACKAGES="DDG4 DDDetectors DDRec UtilityApps" \
  -DDD4HEP_USE_GEANT4=ON \
  -DDD4HEP_USE_XERCESC=ON \
  -DDD4HEP_USE_EDM4HEP=ON
cmake --build ~/cern/build/dd4hep/01-31 --target install

export CMAKE_PREFIX_PATH="~/cern/install/dd4hep/01-31:$CMAKE_PREFIX_PATH"

###

cmake -S ~/cern/source/hepmc3/3.3.1 -B ~/cern/build/hepmc3/3.3.1 \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=20 \
  -DCMAKE_INSTALL_PREFIX=~/cern/install/hepmc3/3.3.1 \
  -DHEPMC3_BUILD_STATIC_LIBS=OFF \
  -DHEPMC3_ENABLE_PYTHON=OFF \
  -DHEPMC3_ENABLE_ROOTIO=ON \
  -DHEPMC3_ENABLE_SEARCH=OFF
cmake --build ~/cern/build/hepmc3/3.3.1 --target install

export CMAKE_PREFIX_PATH="~/cern/install/hepmc3/3.3.1:$CMAKE_PREFIX_PATH"
