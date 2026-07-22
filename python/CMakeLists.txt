# Find the active interpreter and its extension-module development files.
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# Python extension module
# NO_EXTRAS: keep symbols (pybind11 would strip in Release); LTO still applies
# via the global CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELEASE setting.
pybind11_add_module(pysuperansac MODULE NO_EXTRAS
  pybind_module.cpp
  pybind_functions.cpp
)

# Link the C++ core library
target_link_libraries(pysuperansac PRIVATE SupeRANSAC)

# setup-python and PEP 517 isolation place Python and pybind11 under absolute
# runner paths. Remap them before compiling so __FILE__ and compiler records do
# not disclose hosted-tool-cache or temporary build locations.
if(MSVC)
  get_filename_component(SUPERANSAC_PYTHON_ROOT "${Python_EXECUTABLE}" DIRECTORY)
  file(TO_NATIVE_PATH "${SUPERANSAC_PYTHON_ROOT}"
    SUPERANSAC_PYTHON_ROOT_NATIVE)
  target_compile_options(pysuperansac PRIVATE
    "/pathmap:${SUPERANSAC_PYTHON_ROOT_NATIVE}=.python")
  foreach(SUPERANSAC_PYBIND11_INCLUDE IN LISTS pybind11_INCLUDE_DIRS)
    file(TO_NATIVE_PATH "${SUPERANSAC_PYBIND11_INCLUDE}"
      SUPERANSAC_PYBIND11_INCLUDE_NATIVE)
    target_compile_options(pysuperansac PRIVATE
      "/pathmap:${SUPERANSAC_PYBIND11_INCLUDE_NATIVE}=.pybind11")
  endforeach()
endif()

# Ensure loader finds the sibling core .so at runtime
set_target_properties(pysuperansac PROPERTIES
  CXX_VISIBILITY_PRESET default
  VISIBILITY_INLINES_HIDDEN NO
)

if(NOT WIN32)
  set_target_properties(pysuperansac PROPERTIES
    BUILD_RPATH   "$ORIGIN"
    INSTALL_RPATH "$ORIGIN"
  )
endif()

# LTO can stay enabled globally; disable here if needed
# set_property(TARGET pysuperansac PROPERTY INTERPROCEDURAL_OPTIMIZATION_RELEASE FALSE)

# Install module next to the core .so
install(TARGETS pysuperansac
  LIBRARY DESTINATION . COMPONENT python
  RUNTIME DESTINATION . COMPONENT python
)
