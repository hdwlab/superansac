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

add_executable(superansac_graph_cut_optimizer_test
  test_graph_cut_optimizer.cpp
)
target_link_libraries(superansac_graph_cut_optimizer_test PRIVATE
  SupeRANSAC
)
add_test(
  NAME graph_cut_optimizer
  COMMAND superansac_graph_cut_optimizer_test
)
