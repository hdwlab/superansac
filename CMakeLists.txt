cmake_minimum_required(VERSION 3.21)
project(SupeRANSAC LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# ---- Build shape ----
if(WIN32)
  set(SUPERANSAC_SHARED_CORE_DEFAULT OFF)
else()
  set(SUPERANSAC_SHARED_CORE_DEFAULT ON)
endif()
option(SUPERANSAC_BUILD_SHARED_CORE
  "Build the C++ core as a shared library"
  ${SUPERANSAC_SHARED_CORE_DEFAULT})
option(SUPERANSAC_BUILD_TESTS "Build SupeRANSAC tests" OFF)

# ---- Optional fast-math (ON for backward compatibility) ----
option(SUPERANSAC_ENABLE_FAST_MATH "Enable aggressive fast-math" ON)

# ---- Flag probes ----
include(CheckCXXCompilerFlag)
function(add_flag_if_supported flag)
  string(REPLACE "=" "_" flag_var "${flag}")
  string(REGEX REPLACE "^-+" "" flag_var "${flag_var}")
  string(REPLACE "-" "_" flag_var "${flag_var}")
  check_cxx_compiler_flag("${flag}" "HAS_${flag_var}")
  if(HAS_${flag_var})
    add_compile_options($<$<CONFIG:Release>:${flag}>)
  endif()
endfunction()

# ---- Baseline high-performance flags ----
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  add_flag_if_supported(-O3)
  add_flag_if_supported(-march=native)
  add_flag_if_supported(-mtune=native)
  add_flag_if_supported(-fno-plt)
  add_flag_if_supported(-funroll-loops)
  add_flag_if_supported(-ftree-vectorize)
  add_flag_if_supported(-fomit-frame-pointer)
  add_flag_if_supported(-finline-functions)
  add_flag_if_supported(-fprefetch-loop-arrays)
  add_flag_if_supported(-fno-semantic-interposition)
  add_flag_if_supported(-fno-trapping-math)
  add_compile_options($<$<CONFIG:Release>:-DNDEBUG>)
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
  add_flag_if_supported(-O3)
  add_flag_if_supported(-march=native)
  add_flag_if_supported(-mtune=native)
  check_cxx_compiler_flag("-flto=thin" HAS_FLTO_THIN)
  if(HAS_FLTO_THIN)
    add_compile_options($<$<CONFIG:Release>:-flto=thin>)
    add_link_options($<$<CONFIG:Release>:-flto=thin>)
  else()
    add_flag_if_supported(-flto)
    add_link_options($<$<CONFIG:Release>:-flto>)
  endif()
  add_flag_if_supported(-funroll-loops)
  add_flag_if_supported(-fomit-frame-pointer)
  add_flag_if_supported(-finline-functions)
  add_compile_options($<$<CONFIG:Release>:-DNDEBUG>)
elseif(MSVC)
  add_compile_options(
    $<$<CONFIG:Release>:/O2>
    $<$<CONFIG:Release>:/Oi>
    $<$<CONFIG:Release>:/GL>
    $<$<CONFIG:Release>:/Gy>
    $<$<CONFIG:Release>:/DNDEBUG>
    $<$<CONFIG:Release>:/MP>
    $<$<CONFIG:Release>:/Zc:inline>
    $<$<CONFIG:Release>:/W0>
  )
  add_link_options($<$<CONFIG:Release>:/LTCG>)
endif()

# clang-cl takes the Clang optimization branch above but uses the MSVC ABI.
# Apply Windows runtime and reproducibility settings to both cl and clang-cl.
if(MSVC)
  file(TO_NATIVE_PATH "${PROJECT_SOURCE_DIR}" SUPERANSAC_SOURCE_PATH_NATIVE)
  file(TO_NATIVE_PATH "${PROJECT_BINARY_DIR}" SUPERANSAC_BUILD_PATH_NATIVE)
  add_compile_options(
    "/pathmap:${SUPERANSAC_SOURCE_PATH_NATIVE}=."
    "/pathmap:${SUPERANSAC_BUILD_PATH_NATIVE}=.build"
  )
  add_link_options($<$<CONFIG:Release>:/Brepro>)
  set(CMAKE_MSVC_RUNTIME_LIBRARY
    "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
endif()

# ---- Optional fast-math flags ----
if(SUPERANSAC_ENABLE_FAST_MATH)
  if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    add_flag_if_supported(-ffast-math)
    add_flag_if_supported(-fno-math-errno)
    add_flag_if_supported(-ffp-contract=fast)
  elseif(MSVC)
    add_compile_options($<$<CONFIG:Release>:/fp:fast>)
  endif()
endif()

# ---- IPO/LTO in a portable way ----
include(CheckIPOSupported)
check_ipo_supported(RESULT ipo_supported OUTPUT ipo_msg)
if(ipo_supported)
  set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELEASE ON)
endif()

# ---- Eigen: disable debug in release ----
add_compile_definitions($<$<CONFIG:Release>:EIGEN_NO_DEBUG>)

# ---- Modern pybind11 finder hint (silences CMP0148 warning downstream) ----
set(PYBIND11_FINDPYTHON ON)

add_subdirectory(src)
add_subdirectory(python)

if(SUPERANSAC_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests/cpp)
endif()
