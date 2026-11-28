cmake_minimum_required(VERSION 3.20)
project(DenseMaterialFollowup LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_BUILD_TYPE Release)
set(DEPS /Users/andreas/cern/source/acts/ci-dependencies/.spack-env/view CACHE PATH "Dependency view")
set(ACTS_SOURCE /Users/andreas/cern/source/acts/acts/dev3 CACHE PATH "ACTS source with fixes")
set(ACTS_BUILD /Users/andreas/cern/build/acts/acts/dev3 CACHE PATH "Compatible ACTS build")
set(PATCHED_CODEGEN "" CACHE PATH "Generated header root containing codegen/sympy_stepper_math.hpp")
if(NOT EXISTS "${PATCHED_CODEGEN}/codegen/sympy_stepper_math.hpp")
 message(FATAL_ERROR "Generate the patched stepper header and set PATCHED_CODEGEN; see README")
endif()
list(PREPEND CMAKE_PREFIX_PATH ${DEPS})
find_package(Geant4 REQUIRED)
find_package(Eigen3 REQUIRED)
add_library(patched-stepper OBJECT
 ${ACTS_SOURCE}/Core/src/Material/Interactions.cpp
 ${ACTS_SOURCE}/Core/src/Propagator/SympyStepper.cpp
 ${ACTS_SOURCE}/Core/src/Propagator/detail/SympyStepDenseJac.cpp
 ${ACTS_SOURCE}/Core/src/Propagator/detail/SympyStepDenseNoJac.cpp
 ${ACTS_SOURCE}/Core/src/Propagator/detail/SympyStepVacuumJac.cpp
 ${ACTS_SOURCE}/Core/src/Propagator/detail/SympyStepVacuumNoJac.cpp)
target_include_directories(patched-stepper BEFORE PRIVATE ${PATCHED_CODEGEN})
target_include_directories(patched-stepper PRIVATE ${ACTS_SOURCE}/Core/include ${ACTS_BUILD}/Core/include)
target_include_directories(patched-stepper SYSTEM PRIVATE ${DEPS}/include)
target_link_libraries(patched-stepper PRIVATE Eigen3::Eigen)
add_executable(scattering scattering.cpp)
target_include_directories(scattering PRIVATE ${Geant4_INCLUDE_DIRS})
target_link_libraries(scattering PRIVATE ${Geant4_LIBRARIES})
foreach(name acts rates)
 add_executable(${name} ${name}.cpp)
 target_include_directories(${name} PRIVATE ${ACTS_SOURCE}/Core/include ${ACTS_BUILD}/Core/include ${ACTS_SOURCE}/Tests/CommonHelpers/include ${Geant4_INCLUDE_DIRS})
 target_include_directories(${name} SYSTEM PRIVATE ${DEPS}/include)
 target_link_libraries(${name} PRIVATE patched-stepper Eigen3::Eigen ${ACTS_BUILD}/lib/libActsCore.dylib ${Geant4_LIBRARIES})
endforeach()
