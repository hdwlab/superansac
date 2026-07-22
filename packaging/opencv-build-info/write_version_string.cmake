# OpenCV's core target lists this generated file as a source. The normal
# finalization writes host paths and timestamps into it, so the wheel triplet
# disables that finalization and installs this stable replacement instead.
if(PROJECT_NAME STREQUAL "OpenCV")
  set(_superansac_version_string
    "${CMAKE_BINARY_DIR}/modules/core/version_string.inc")
  file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/modules/core")
  configure_file(
    "${CMAKE_CURRENT_LIST_DIR}/version_string.inc"
    "${_superansac_version_string}"
    COPYONLY)
  unset(_superansac_version_string)
endif()
