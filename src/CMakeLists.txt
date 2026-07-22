# Find Eigen3
find_package(Eigen3 CONFIG REQUIRED)

# Find OpenCV
find_package(OpenCV REQUIRED COMPONENTS core calib3d)

# Keep this list explicit. Recursive globs previously compiled unrelated
# vendored sources into the wheel without making that dependency visible.
set(SUPERANSAC_SOURCE_FILES
  ${PROJECT_SOURCE_DIR}/include/estimators/numerical_optimizer/colmap_models.cc
  ${PROJECT_SOURCE_DIR}/include/estimators/numerical_optimizer/essential.cc
)

if(SUPERANSAC_BUILD_SHARED_CORE)
  add_library(SupeRANSAC SHARED)
else()
  add_library(SupeRANSAC STATIC)
endif()
target_sources(SupeRANSAC PRIVATE
  superansac.cpp
  ${SUPERANSAC_SOURCE_FILES}
)

# Give a unique, stable SONAME to avoid stale copies being picked at runtime
set_target_properties(SupeRANSAC PROPERTIES
  OUTPUT_NAME superansac_core
  SOVERSION 1
  VERSION   1.0.0
  POSITION_INDEPENDENT_CODE ON
  CXX_VISIBILITY_PRESET default
  VISIBILITY_INLINES_HIDDEN NO
)

# Public includes
target_include_directories(SupeRANSAC PUBLIC
  ${PROJECT_SOURCE_DIR}/include
  ${OpenCV_INCLUDE_DIRS}
)

# Link deps
target_link_libraries(SupeRANSAC
  PUBLIC
    Eigen3::Eigen
    ${OpenCV_LIBS}
)

# A shared core must be installed next to the Python module. A static core is
# linked into the extension and must not leak a .lib/.a into the wheel.
if(SUPERANSAC_BUILD_SHARED_CORE)
  install(TARGETS SupeRANSAC
    LIBRARY DESTINATION . COMPONENT python
    RUNTIME DESTINATION . COMPONENT python
  )
endif()
