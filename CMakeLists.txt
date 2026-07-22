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
option(SUPERANSAC_ENABLE_NATIVE_ARCH
  "Tune generated code for the build host (unsafe for distributable wheels)"
  OFF)

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
  if(SUPERANSAC_ENABLE_NATIVE_ARCH)
    add_flag_if_supported(-march=native)
    add_flag_if_supported(-mtune=native)
  endif()
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
  if(MSVC)
    add_compile_options(
      $<$<CONFIG:Release>:/O2>
      $<$<CONFIG:Release>:/Ob3>
      $<$<CONFIG:Release>:/Oi>
      $<$<CONFIG:Release>:/Gy>
      $<$<CONFIG:Release>:/Gw>
      $<$<CONFIG:Release>:/DNDEBUG>
      $<$<CONFIG:Release>:/MP>
      $<$<CONFIG:Release>:/Zc:inline>
      $<$<CONFIG:Release>:/W0>
      $<$<CONFIG:Release>:/clang:-O3>
      $<$<CONFIG:Release>:/clang:-funroll-loops>
      $<$<CONFIG:Release>:/clang:-fomit-frame-pointer>
      $<$<CONFIG:Release>:/clang:-finline-functions>
    )
  else()
    add_flag_if_supported(-O3)
    if(SUPERANSAC_ENABLE_NATIVE_ARCH)
      add_flag_if_supported(-march=native)
      add_flag_if_supported(-mtune=native)
    endif()
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
  endif()
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
  if(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    add_compile_options(
      "/clang:-ffile-prefix-map=${PROJECT_SOURCE_DIR}=."
      "/clang:-ffile-prefix-map=${PROJECT_BINARY_DIR}=.build"
    )
  else()
    file(TO_NATIVE_PATH "${PROJECT_SOURCE_DIR}" SUPERANSAC_SOURCE_PATH_NATIVE)
    file(TO_NATIVE_PATH "${PROJECT_BINARY_DIR}" SUPERANSAC_BUILD_PATH_NATIVE)
    add_compile_options(
      $<$<CONFIG:Release>:/experimental:deterministic>
      "/pathmap:${SUPERANSAC_SOURCE_PATH_NATIVE}=."
      "/pathmap:${SUPERANSAC_BUILD_PATH_NATIVE}=.build"
    )
  endif()
  add_link_options($<$<CONFIG:Release>:/Brepro>)
  set(CMAKE_MSVC_RUNTIME_LIBRARY
    "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
endif()

# ---- Optional fast-math flags ----
if(SUPERANSAC_ENABLE_FAST_MATH)
  if(MSVC)
    add_compile_options($<$<CONFIG:Release>:/fp:fast>)
  elseif(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    add_flag_if_supported(-ffast-math)
    add_flag_if_supported(-fno-math-errno)
    add_flag_if_supported(-ffp-contract=fast)
  endif()
endif()

# ---- IPO/LTO in a portable way ----
include(CheckIPOSupported)
check_ipo_supported(RESULT ipo_supported OUTPUT ipo_msg)
if(ipo_supported)
  set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELEASE ON)
endif()

# Keep optimization decisions visible in CI. Directory options are inherited
# by the core and Python subdirectories created below.
get_directory_property(SUPERANSAC_EFFECTIVE_COMPILE_OPTIONS COMPILE_OPTIONS)
get_directory_property(SUPERANSAC_EFFECTIVE_LINK_OPTIONS LINK_OPTIONS)
message(STATUS
  "SupeRANSAC compiler: id=${CMAKE_CXX_COMPILER_ID}; "
  "frontend=${CMAKE_CXX_COMPILER_FRONTEND_VARIANT}; "
  "version=${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS
  "SupeRANSAC release: native_arch=${SUPERANSAC_ENABLE_NATIVE_ARCH}; "
  "fast_math=${SUPERANSAC_ENABLE_FAST_MATH}; ipo=${ipo_supported}")
message(STATUS
  "SupeRANSAC compile options: ${SUPERANSAC_EFFECTIVE_COMPILE_OPTIONS}")
message(STATUS
  "SupeRANSAC link options: ${SUPERANSAC_EFFECTIVE_LINK_OPTIONS}")

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
