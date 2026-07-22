set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE static)
set(VCPKG_BUILD_TYPE release)

# All release inputs live below the repository root in CI. Map that prefix out
# of __FILE__, PDB, and other compiler records so the wheel does not disclose a
# GitHub runner or vcpkg buildtree path.
get_filename_component(SUPERANSAC_REPOSITORY_ROOT
  "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)
file(TO_NATIVE_PATH "${SUPERANSAC_REPOSITORY_ROOT}"
  SUPERANSAC_REPOSITORY_ROOT_NATIVE)
file(TO_NATIVE_PATH
  "${SUPERANSAC_REPOSITORY_ROOT}/packaging/opencv-build-info"
  SUPERANSAC_OPENCV_BUILD_INFO_NATIVE)

set(VCPKG_C_FLAGS_RELEASE
  "/pathmap:${SUPERANSAC_REPOSITORY_ROOT_NATIVE}=. /Brepro")
set(VCPKG_CXX_FLAGS_RELEASE
  "/pathmap:${SUPERANSAC_REPOSITORY_ROOT_NATIVE}=. /Brepro /I\"${SUPERANSAC_OPENCV_BUILD_INFO_NATIVE}\"")

# OpenCV normally embeds the compiler, install prefix, and full vcpkg paths in
# cv::getBuildInformation(). Supply a stable replacement and omit /Z7 records.
set(VCPKG_CMAKE_CONFIGURE_OPTIONS_RELEASE
  "-DBUILD_WITH_DEBUG_INFO=OFF"
  "-DOPENCV_SKIP_STATUS_FINALIZATION=ON")

set(VCPKG_HASH_ADDITIONAL_FILES
  "${SUPERANSAC_REPOSITORY_ROOT}/packaging/opencv-build-info/version_string.inc")
