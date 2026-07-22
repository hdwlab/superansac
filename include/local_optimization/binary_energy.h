// Copyright (c) 2026 Human Dataware Lab. Co., Ltd.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <queue>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace superansac::local_optimization {

// Minimizes binary energies consisting of unary and submodular pairwise terms
// with an iterative Dinic maximum-flow implementation. Label 0 is the source
// segment and label 1 is the sink segment.
template <typename Capacity>
class BinaryEnergy {
    static_assert(std::is_floating_point_v<Capacity>,
                  "BinaryEnergy requires a floating-point capacity type.");

public:
    using Variable = std::size_t;

    enum class Segment {
        Source,
        Sink,
    };

    explicit BinaryEnergy(const std::size_t expected_variables = 0,
                          const std::size_t expected_pairwise_terms = 0) {
        unary_terms_.reserve(expected_variables);
        pairwise_terms_.reserve(expected_pairwise_terms);
        segments_.reserve(expected_variables);
    }

    void reset() noexcept {
        unary_terms_.clear();
        pairwise_terms_.clear();
        segments_.clear();
        constant_ = Capacity{0};
        minimized_ = false;
    }

    Variable add_node(const std::size_t count = 1) {
        const Variable first = unary_terms_.size();
        unary_terms_.resize(first + count, {Capacity{0}, Capacity{0}});
        minimized_ = false;
        return first;
    }

    void add_term1(const Variable variable,
                   const Capacity energy_if_source,
                   const Capacity energy_if_sink) {
        check_variable(variable);
        check_finite(energy_if_source, "Unary source energy");
        check_finite(energy_if_sink, "Unary sink energy");
        unary_terms_[variable][0] += energy_if_source;
        unary_terms_[variable][1] += energy_if_sink;
        check_finite(unary_terms_[variable][0], "Accumulated unary source energy");
        check_finite(unary_terms_[variable][1], "Accumulated unary sink energy");
        minimized_ = false;
    }

    // Adds E(x, y) with values E00, E01, E10, E11. Such a term is graph
    // representable exactly when E00 + E11 <= E01 + E10.
    void add_term2(const Variable first,
                   const Variable second,
                   const Capacity energy_00,
                   const Capacity energy_01,
                   const Capacity energy_10,
                   const Capacity energy_11) {
        check_variable(first);
        check_variable(second);
        check_finite(energy_00, "Pairwise E00");
        check_finite(energy_01, "Pairwise E01");
        check_finite(energy_10, "Pairwise E10");
        check_finite(energy_11, "Pairwise E11");

        if (first == second) {
            add_term1(first, energy_00, energy_11);
            return;
        }

        const Capacity directed_capacity =
            energy_01 + energy_10 - energy_00 - energy_11;
        check_finite(directed_capacity, "Pairwise directed capacity");
        const Capacity scale = std::max(
            {Capacity{1}, std::abs(energy_00), std::abs(energy_01),
             std::abs(energy_10), std::abs(energy_11)});
        const Capacity tolerance =
            Capacity{64} * std::numeric_limits<Capacity>::epsilon() * scale;
        if (directed_capacity < -tolerance) {
            throw std::invalid_argument(
                "Pairwise energy is not submodular (E00 + E11 > E01 + E10).");
        }

        // E(x,y) = E00 + (E10-E00)x + (E11-E10)y
        //          + (E01+E10-E00-E11)[x=0,y=1].
        // The last term is a directed first->second cut edge.
        constant_ += energy_00;
        unary_terms_[first][1] += energy_10 - energy_00;
        unary_terms_[second][1] += energy_11 - energy_10;
        pairwise_terms_.push_back(
            {first, second, std::max(Capacity{0}, directed_capacity)});

        check_finite(constant_, "Accumulated energy constant");
        check_finite(unary_terms_[first][1], "Accumulated pairwise unary energy");
        check_finite(unary_terms_[second][1], "Accumulated pairwise unary energy");
        minimized_ = false;
    }

    Capacity minimize() {
        if (unary_terms_.empty()) {
            segments_.clear();
            minimized_ = true;
            return constant_;
        }

        const std::size_t variable_count = unary_terms_.size();
        const std::size_t source_vertex = variable_count;
        const std::size_t sink_vertex = variable_count + 1;
        prepare_flow_graph(variable_count + 2, variable_count);

        Capacity normalized_constant = constant_;
        Capacity largest_capacity = Capacity{1};

        for (std::size_t variable = 0; variable < variable_count; ++variable) {
            const Capacity minimum =
                std::min(unary_terms_[variable][0], unary_terms_[variable][1]);
            normalized_constant += minimum;
            const Capacity source_energy = unary_terms_[variable][0] - minimum;
            const Capacity sink_energy = unary_terms_[variable][1] - minimum;

            // A source->variable edge is cut when the variable is in Sink.
            add_arc(source_vertex, variable, sink_energy);
            // A variable->sink edge is cut when the variable is in Source.
            add_arc(variable, sink_vertex, source_energy);
            largest_capacity =
                std::max({largest_capacity, source_energy, sink_energy});
        }

        for (const PairwiseTerm& term : pairwise_terms_) {
            add_arc(term.first, term.second, term.capacity);
            largest_capacity = std::max(largest_capacity, term.capacity);
        }

        const Capacity flow = maximum_flow(source_vertex, sink_vertex);

        const Capacity residual_tolerance =
            Capacity{64} * std::numeric_limits<Capacity>::epsilon() * largest_capacity;
        std::vector<unsigned char> source_reachable(variable_count + 2, 0);
        std::queue<std::size_t> frontier;
        source_reachable[source_vertex] = 1;
        frontier.push(source_vertex);
        while (!frontier.empty()) {
            const std::size_t current = frontier.front();
            frontier.pop();
            for (const FlowEdge& edge : flow_graph_[current]) {
                if (edge.residual <= residual_tolerance) {
                    continue;
                }
                const std::size_t target = edge.target;
                if (source_reachable[target] == 0) {
                    source_reachable[target] = 1;
                    frontier.push(target);
                }
            }
        }

        segments_.resize(variable_count);
        for (std::size_t variable = 0; variable < variable_count; ++variable) {
            segments_[variable] = source_reachable[variable] != 0
                                      ? Segment::Source
                                      : Segment::Sink;
        }
        minimized_ = true;
        return normalized_constant + flow;
    }

    Segment what_segment(const Variable variable) const {
        check_variable(variable);
        if (!minimized_) {
            throw std::logic_error("BinaryEnergy must be minimized before querying labels.");
        }
        return segments_[variable];
    }

    int get_var(const Variable variable) const {
        return what_segment(variable) == Segment::Source ? 0 : 1;
    }

    std::size_t variable_count() const noexcept {
        return unary_terms_.size();
    }

private:
    using FlowIndex = std::uint32_t;

    struct FlowEdge {
        FlowIndex target;
        FlowIndex reverse;
        Capacity residual;
    };

    struct PairwiseTerm {
        Variable first;
        Variable second;
        Capacity capacity;
    };

    static void check_finite(const Capacity value, const char* description) {
        if (!is_finite(value)) {
            throw std::invalid_argument(std::string(description) + " must be finite.");
        }
    }

    // std::isfinite may be folded to true when the project is built with
    // -ffast-math or /fp:fast. Inspect the IEEE-754 exponent instead so input
    // validation remains active under the production optimization settings.
    static bool is_finite(const Capacity value) noexcept {
        static_assert(std::numeric_limits<Capacity>::is_iec559,
                      "BinaryEnergy requires an IEEE-754 capacity type.");
        if constexpr (sizeof(Capacity) == sizeof(std::uint32_t)) {
            std::uint32_t bits = 0;
            std::memcpy(&bits, &value, sizeof(bits));
            return (bits & UINT32_C(0x7f800000)) != UINT32_C(0x7f800000);
        } else if constexpr (sizeof(Capacity) == sizeof(std::uint64_t)) {
            std::uint64_t bits = 0;
            std::memcpy(&bits, &value, sizeof(bits));
            return (bits & UINT64_C(0x7ff0000000000000)) !=
                   UINT64_C(0x7ff0000000000000);
        } else {
            return std::isfinite(value);
        }
    }

    void check_variable(const Variable variable) const {
        if (variable >= unary_terms_.size()) {
            throw std::out_of_range("BinaryEnergy variable index is out of range.");
        }
    }

    void prepare_flow_graph(const std::size_t vertex_count,
                            const std::size_t variable_count) {
        if (vertex_count > std::numeric_limits<FlowIndex>::max()) {
            throw std::length_error("BinaryEnergy graph is too large.");
        }
        flow_graph_.resize(vertex_count);
        degree_counts_.assign(vertex_count, 0);
        degree_counts_[variable_count] = variable_count;
        degree_counts_[variable_count + 1] = variable_count;
        for (std::size_t variable = 0; variable < variable_count; ++variable) {
            degree_counts_[variable] = 2;
        }
        for (const PairwiseTerm& term : pairwise_terms_) {
            ++degree_counts_[term.first];
            ++degree_counts_[term.second];
        }
        for (std::size_t vertex = 0; vertex < vertex_count; ++vertex) {
            flow_graph_[vertex].clear();
            flow_graph_[vertex].reserve(degree_counts_[vertex]);
        }
        levels_.resize(vertex_count);
        next_edges_.resize(vertex_count);
        path_vertices_.reserve(vertex_count);
        path_edges_.reserve(vertex_count);
        path_capacities_.reserve(vertex_count);
    }

    void add_arc(const std::size_t from,
                 const std::size_t to,
                 const Capacity value) {
        if (value < Capacity{0} || !is_finite(value)) {
            throw std::invalid_argument("Graph capacities must be finite and non-negative.");
        }
        if (flow_graph_[from].size() >= std::numeric_limits<FlowIndex>::max() ||
            flow_graph_[to].size() >= std::numeric_limits<FlowIndex>::max()) {
            throw std::length_error("BinaryEnergy vertex degree is too large.");
        }
        const FlowIndex forward_index =
            static_cast<FlowIndex>(flow_graph_[from].size());
        const FlowIndex reverse_index =
            static_cast<FlowIndex>(flow_graph_[to].size());
        flow_graph_[from].push_back(
            {static_cast<FlowIndex>(to), reverse_index, value});
        flow_graph_[to].push_back(
            {static_cast<FlowIndex>(from), forward_index, Capacity{0}});
    }

    bool build_level_graph(const std::size_t source,
                           const std::size_t sink) {
        std::fill(levels_.begin(), levels_.end(), -1);
        std::queue<std::size_t> frontier;
        levels_[source] = 0;
        frontier.push(source);
        while (!frontier.empty()) {
            const std::size_t current = frontier.front();
            frontier.pop();
            for (const FlowEdge& edge : flow_graph_[current]) {
                if (edge.residual <= Capacity{0} || levels_[edge.target] >= 0) {
                    continue;
                }
                levels_[edge.target] = levels_[current] + 1;
                if (edge.target == sink) {
                    return true;
                }
                frontier.push(edge.target);
            }
        }
        return levels_[sink] >= 0;
    }

    Capacity send_flow(const std::size_t source,
                       const std::size_t sink) {
        path_vertices_.clear();
        path_edges_.clear();
        path_capacities_.clear();
        path_vertices_.push_back(source);
        path_capacities_.push_back(std::numeric_limits<Capacity>::max());

        while (!path_vertices_.empty()) {
            const std::size_t current = path_vertices_.back();
            if (current == sink) {
                const Capacity sent = path_capacities_.back();
                for (std::size_t depth = 0; depth < path_edges_.size(); ++depth) {
                    FlowEdge& edge =
                        flow_graph_[path_vertices_[depth]][path_edges_[depth]];
                    edge.residual -= sent;
                    flow_graph_[edge.target][edge.reverse].residual += sent;
                }
                return sent;
            }

            FlowIndex& edge_index = next_edges_[current];
            while (edge_index < flow_graph_[current].size()) {
                const FlowEdge& edge = flow_graph_[current][edge_index];
                if (edge.residual > Capacity{0} &&
                    levels_[edge.target] == levels_[current] + 1) {
                    break;
                }
                ++edge_index;
            }
            if (edge_index < flow_graph_[current].size()) {
                const FlowEdge& edge = flow_graph_[current][edge_index];
                path_edges_.push_back(edge_index);
                path_vertices_.push_back(edge.target);
                path_capacities_.push_back(
                    std::min(path_capacities_.back(), edge.residual));
                continue;
            }

            // This vertex cannot reach the sink in the current level graph.
            levels_[current] = -1;
            path_vertices_.pop_back();
            path_capacities_.pop_back();
            if (!path_edges_.empty()) {
                path_edges_.pop_back();
                if (!path_vertices_.empty()) {
                    ++next_edges_[path_vertices_.back()];
                }
            }
        }
        return Capacity{0};
    }

    Capacity maximum_flow(const std::size_t source,
                          const std::size_t sink) {
        Capacity total = Capacity{0};
        while (build_level_graph(source, sink)) {
            std::fill(next_edges_.begin(), next_edges_.end(), FlowIndex{0});
            while (true) {
                const Capacity sent = send_flow(source, sink);
                if (sent <= Capacity{0}) {
                    break;
                }
                total += sent;
                check_finite(total, "Maximum flow");
            }
        }
        return total;
    }

    std::vector<std::array<Capacity, 2>> unary_terms_;
    std::vector<PairwiseTerm> pairwise_terms_;
    std::vector<Segment> segments_;
    std::vector<std::vector<FlowEdge>> flow_graph_;
    std::vector<std::size_t> degree_counts_;
    std::vector<int> levels_;
    std::vector<FlowIndex> next_edges_;
    std::vector<std::size_t> path_vertices_;
    std::vector<FlowIndex> path_edges_;
    std::vector<Capacity> path_capacities_;
    Capacity constant_ = Capacity{0};
    bool minimized_ = false;
};

}  // namespace superansac::local_optimization
