// Copyright (c) 2026 Human Dataware Lab. Co., Ltd.
// SPDX-License-Identifier: MIT

#include "local_optimization/graph_cut_ransac_optimizer.h"

#include <array>
#include <cstddef>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

using superansac::local_optimization::detail::estimateModelFromSample;
using superansac::local_optimization::detail::mapSampleToDataIndices;
using superansac::local_optimization::detail::sampleSizeForInlierPool;
using superansac::models::Model;

class RecordingEstimator {
public:
    explicit RecordingEstimator(const std::size_t minimal_sample_size)
        : minimal_sample_size_(minimal_sample_size) {}

    std::size_t sampleSize() const {
        return minimal_sample_size_;
    }

    bool estimateModel(const DataMatrix&,
                       const std::size_t*,
                       std::vector<Model>*) const {
        ++minimal_calls;
        return minimal_result;
    }

    bool estimateModelNonminimal(const DataMatrix&,
                                 const std::size_t*,
                                 const std::size_t&,
                                 std::vector<Model>*,
                                 const double*) const {
        ++nonminimal_calls;
        return nonminimal_result;
    }

    mutable std::size_t minimal_calls = 0;
    mutable std::size_t nonminimal_calls = 0;
    bool minimal_result = true;
    bool nonminimal_result = true;

private:
    std::size_t minimal_sample_size_;
};

void check_sample_mapping() {
    const std::vector<std::size_t> inliers{4, 17, 29, 63};
    std::array<std::size_t, 3> sample{2, 0, 3};

    mapSampleToDataIndices(inliers, sample.size(), sample.data());

    const std::array<std::size_t, 3> expected{29, 4, 63};
    if (sample != expected) {
        throw std::runtime_error("Pool-local sample indices were not mapped to data rows.");
    }
}

void check_sample_size() {
    if (sampleSizeForInlierPool(0, 28) != 0 ||
        sampleSizeForInlierPool(4, 28) != 4 ||
        sampleSizeForInlierPool(28, 28) != 28 ||
        sampleSizeForInlierPool(29, 28) != 28) {
        throw std::runtime_error("The bounded sample size dropped or exceeded an inlier.");
    }
}

void check_estimator_dispatch() {
    DataMatrix data;
    const std::array<std::size_t, 6> sample{0, 1, 2, 3, 4, 5};
    std::vector<Model> models;
    RecordingEstimator estimator(4);

    if (!estimateModelFromSample(
            data, sample.data(), 6, &estimator, &models)) {
        throw std::runtime_error("Non-minimal estimation unexpectedly failed.");
    }
    if (estimator.nonminimal_calls != 1 || estimator.minimal_calls != 0) {
        throw std::runtime_error("A non-minimal sample did not use exactly one estimator.");
    }

    if (!estimateModelFromSample(
            data, sample.data(), 4, &estimator, &models)) {
        throw std::runtime_error("Minimal estimation unexpectedly failed.");
    }
    if (estimator.nonminimal_calls != 1 || estimator.minimal_calls != 1) {
        throw std::runtime_error("A minimal sample did not use exactly one estimator.");
    }

    estimator.nonminimal_result = false;
    if (estimateModelFromSample(
            data, sample.data(), 6, &estimator, &models)) {
        throw std::runtime_error("Estimator failure was not propagated.");
    }
    if (estimator.nonminimal_calls != 2 || estimator.minimal_calls != 1) {
        throw std::runtime_error("A failed non-minimal fit invoked the minimal estimator.");
    }
}

}  // namespace

int main() {
    try {
        check_sample_size();
        check_sample_mapping();
        check_estimator_dispatch();
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    std::cout << "Graph-cut optimizer tests passed.\n";
    return 0;
}
