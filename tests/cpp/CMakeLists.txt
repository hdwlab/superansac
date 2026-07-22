add_executable(superansac_binary_energy_test
  test_binary_energy.cpp
)
target_include_directories(superansac_binary_energy_test PRIVATE
  ${PROJECT_SOURCE_DIR}/include
)
add_test(
  NAME binary_energy
  COMMAND superansac_binary_energy_test
)
