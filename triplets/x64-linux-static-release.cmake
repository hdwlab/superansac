set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CMAKE_SYSTEM_NAME Linux)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE static)
set(VCPKG_BUILD_TYPE release)

# Distributable wheels must not inherit the hosted runner's ISA. Also remove
# dependency build roots from __FILE__ and debug records before the static
# archives are linked into the Python extension.
set(VCPKG_C_FLAGS_RELEASE
  "-O3 -DNDEBUG -ffile-prefix-map=/opt/vcpkg=.third-party -fdebug-prefix-map=/opt/vcpkg=.third-party -ffile-prefix-map=/opt/vcpkg_installed=.dependencies -fdebug-prefix-map=/opt/vcpkg_installed=.dependencies")
set(VCPKG_CXX_FLAGS_RELEASE "${VCPKG_C_FLAGS_RELEASE}")

# OpenCV normally embeds its compiler, install prefix, and build paths in
# cv::getBuildInformation(). Use the same stable replacement as Windows.
get_filename_component(SUPERANSAC_MANYLINUX_CONFIG_ROOT
  "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)
set(VCPKG_CMAKE_CONFIGURE_OPTIONS_RELEASE
  "-DBUILD_WITH_DEBUG_INFO=OFF"
  "-DCMAKE_PROJECT_INCLUDE=${SUPERANSAC_MANYLINUX_CONFIG_ROOT}/packaging/opencv-build-info/write_version_string.cmake"
  "-DOPENCV_SKIP_STATUS_FINALIZATION=ON"
  "-DWITH_ITT=OFF"
  "-DWITH_LAPACK=OFF"
  "-DWITH_OPENCL=OFF"
  "-DWITH_OPENMP=OFF"
  "-DWITH_TBB=OFF")

set(VCPKG_HASH_ADDITIONAL_FILES
  "${SUPERANSAC_MANYLINUX_CONFIG_ROOT}/packaging/opencv-build-info/version_string.inc"
  "${SUPERANSAC_MANYLINUX_CONFIG_ROOT}/packaging/opencv-build-info/write_version_string.cmake")
