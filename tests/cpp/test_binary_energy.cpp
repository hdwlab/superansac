// Copyright (c) 2026 Human Dataware Lab. Co., Ltd.
// SPDX-License-Identifier: MIT

#include "local_optimization/binary_energy.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <vector>

namespace {

using Energy = superansac::local_optimization::BinaryEnergy<double>;

struct PairwiseTerm {
    std::size_t first;
    std::size_t second;
    std::array<double, 4> values;
};

bool approximately_equal(const double first, const double second) {
    return std::abs(first - second) <=
           1e-9 * std::max({1.0, std::abs(first), std::abs(second)});
}

double evaluate(const std::vector<std::array<double, 2>>& unary,
                const std::vector<PairwiseTerm>& pairwise,
                const std::size_t labels) {
    double value = 0.0;
    for (std::size_t variable = 0; variable < unary.size(); ++variable) {
        value += unary[variable][(labels >> variable) & 1U];
    }
    for (const PairwiseTerm& term : pairwise) {
        const std::size_t first_label = (labels >> term.first) & 1U;
        const std::size_t second_label = (labels >> term.second) & 1U;
        value += term.values[first_label * 2U + second_label];
    }
    return value;
}

void check_random_energies() {
    std::mt19937_64 generator(0x5A17C0FFEEULL);
    std::uniform_real_distribution<double> value_distribution(-4.0, 4.0);
    std::uniform_real_distribution<double> slack_distribution(0.0, 3.0);

    for (std::size_t variable_count = 1; variable_count <= 8; ++variable_count) {
        for (std::size_t repetition = 0; repetition < 200; ++repetition) {
            Energy energy(variable_count, variable_count * 2);
            energy.add_node(variable_count);

            std::vector<std::array<double, 2>> unary(variable_count);
            for (std::size_t variable = 0; variable < variable_count; ++variable) {
                unary[variable] = {value_distribution(generator),
                                   value_distribution(generator)};
                energy.add_term1(variable, unary[variable][0], unary[variable][1]);
            }

            std::vector<PairwiseTerm> pairwise;
            for (std::size_t first = 0; first < variable_count; ++first) {
                for (std::size_t second = first + 1; second < variable_count; ++second) {
                    if ((generator() & 3U) != 0U) {
                        continue;
                    }
                    const double energy_00 = value_distribution(generator);
                    const double energy_01 = value_distribution(generator);
                    const double energy_10 = value_distribution(generator);
                    const double energy_11 = energy_01 + energy_10 - energy_00 -
                                             slack_distribution(generator);
                    pairwise.push_back(
                        {first, second, {energy_00, energy_01, energy_10, energy_11}});
                    energy.add_term2(first, second, energy_00, energy_01,
                                     energy_10, energy_11);
                }
            }

            double brute_force_minimum = std::numeric_limits<double>::infinity();
            for (std::size_t labels = 0; labels < (std::size_t{1} << variable_count);
                 ++labels) {
                brute_force_minimum =
                    std::min(brute_force_minimum, evaluate(unary, pairwise, labels));
            }

            const double graph_minimum = energy.minimize();
            if (!approximately_equal(graph_minimum, brute_force_minimum)) {
                throw std::runtime_error("Min-cut does not match brute force.");
            }

            std::size_t selected_labels = 0;
            for (std::size_t variable = 0; variable < variable_count; ++variable) {
                selected_labels |= static_cast<std::size_t>(energy.get_var(variable))
                                   << variable;
            }
            if (!approximately_equal(evaluate(unary, pairwise, selected_labels),
                                     brute_force_minimum)) {
                throw std::runtime_error("Reported cut is not an optimal labeling.");
            }
        }
    }
}

void check_edge_cases() {
    Energy empty;
    if (!approximately_equal(empty.minimize(), 0.0)) {
        throw std::runtime_error("Empty energy has a non-zero minimum.");
    }

    Energy tie(2, 1);
    tie.add_node(2);
    tie.add_term2(0, 1, 0.0, 1.0, 1.0, 0.0);
    if (!approximately_equal(tie.minimize(), 0.0)) {
        throw std::runtime_error("Tied energy has an incorrect minimum.");
    }

    tie.reset();
    tie.add_node();
    tie.add_term1(0, 3.0, -2.0);
    if (!approximately_equal(tie.minimize(), -2.0) || tie.get_var(0) != 1) {
        throw std::runtime_error("Reset or negative unary normalization failed.");
    }

    Energy tiny(1, 0);
    tiny.add_node();
    tiny.add_term1(0, 0.0, 1e-20);
    if (tiny.minimize() != 0.0 || tiny.get_var(0) != 0) {
        throw std::runtime_error("Tiny positive capacity produced an inconsistent cut.");
    }

    bool non_submodular_rejected = false;
    try {
        Energy invalid(2, 1);
        invalid.add_node(2);
        invalid.add_term2(0, 1, 2.0, 0.0, 0.0, 2.0);
    } catch (const std::invalid_argument&) {
        non_submodular_rejected = true;
    }
    if (!non_submodular_rejected) {
        throw std::runtime_error("Non-submodular energy was accepted.");
    }

    bool non_finite_rejected = false;
    try {
        Energy invalid(1, 0);
        invalid.add_node();
        invalid.add_term1(0, std::numeric_limits<double>::infinity(), 0.0);
    } catch (const std::invalid_argument&) {
        non_finite_rejected = true;
    }
    if (!non_finite_rejected) {
        throw std::runtime_error("Non-finite energy was accepted.");
    }

    // Exercise a path deeper than typical process stack limits. The max-flow
    // search is iterative so large, ordered neighborhoods cannot overflow the
    // Windows thread stack.
    constexpr std::size_t chain_length = 20000;
    Energy chain(chain_length, chain_length - 1);
    chain.add_node(chain_length);
    chain.add_term1(0, 0.0, 1.0);
    chain.add_term1(chain_length - 1, 1.0, 0.0);
    for (std::size_t index = 0; index + 1 < chain_length; ++index) {
        chain.add_term2(index, index + 1, 0.0, 1.0, 0.0, 0.0);
    }
    if (!approximately_equal(chain.minimize(), 1.0)) {
        throw std::runtime_error("Deep-chain minimum is incorrect.");
    }
}

}  // namespace

int main() {
    try {
        check_random_energies();
        check_edge_cases();
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    std::cout << "BinaryEnergy tests passed.\n";
    return 0;
}
