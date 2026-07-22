"""Tests that exercise the public API from an installed wheel."""

from __future__ import annotations

import numpy as np
import pysuperansac
import pytest


def synthetic_homography_case(
    point_count: int = 80,
    *,
    seed: int = 0x5A17,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return correspondences, image sizes, and known inlier indices."""
    rng = np.random.default_rng(seed)
    source = rng.uniform([32.0, 24.0], [608.0, 456.0], (point_count, 2))
    expected = np.array(
        [[1.01, 0.015, 12.0], [-0.01, 0.995, 8.0], [1.0e-5, -2.0e-5, 1.0]],
        dtype=np.float64,
    )
    homogeneous = np.column_stack((source, np.ones(point_count))) @ expected.T
    destination = homogeneous[:, :2] / homogeneous[:, 2:]
    destination += rng.normal(0.0, 0.10, destination.shape)

    outlier_count = max(1, point_count // 5)
    outliers = rng.choice(point_count, outlier_count, replace=False)
    destination[outliers] = rng.uniform([0.0, 0.0], [640.0, 480.0], (outlier_count, 2))
    inliers = np.setdiff1d(np.arange(point_count), outliers)

    correspondences = np.ascontiguousarray(np.column_stack((source, destination)), dtype=np.float64)
    image_sizes = np.array([640.0, 480.0, 640.0, 480.0], dtype=np.float64)
    return correspondences, image_sizes, inliers


def gcransac_settings() -> pysuperansac.RANSACSettings:
    settings = pysuperansac.RANSACSettings()
    settings.min_iterations = 100
    settings.max_iterations = 500
    settings.inlier_threshold = 2.0
    settings.confidence = 0.999
    settings.scoring = pysuperansac.ScoringType.MSAC
    settings.sampler = pysuperansac.SamplerType.Uniform
    settings.neighborhood = pysuperansac.NeighborhoodType.Grid
    settings.local_optimization = pysuperansac.LocalOptimizationType.GCRANSAC
    settings.final_optimization = pysuperansac.LocalOptimizationType.LSQ
    settings.local_opt_k = 1
    settings.use_sprt = False
    return settings


def adversarial_gcransac_case() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return a case where pool-local indices cannot alias the intended inliers."""
    point_count = 1000
    inlier_count = 300
    rng = np.random.default_rng(1)
    source = rng.uniform([50.0, 50.0], [1820.0, 1000.0], (point_count, 2))
    expected = np.array(
        [[1.005, 0.008, 18.0], [-0.006, 0.997, 24.0], [4e-6, -7e-6, 1.0]],
        dtype=np.float64,
    )
    homogeneous = np.column_stack((source, np.ones(point_count))) @ expected.T
    ideal = homogeneous[:, :2] / homogeneous[:, 2:]
    destination = ideal + rng.normal(0.0, 0.8, ideal.shape)
    destination[inlier_count:] = rng.uniform(
        [0.0, 0.0], [1920.0, 1080.0], (point_count - inlier_count, 2)
    )

    # Put every outlier before every inlier. A pool-local index accidentally
    # used as a data-row index therefore selects only outliers.
    permutation = np.concatenate((np.arange(inlier_count, point_count), np.arange(inlier_count)))
    correspondences = np.ascontiguousarray(
        np.column_stack((source, destination))[permutation], dtype=np.float64
    )
    known_inliers = np.arange(point_count - inlier_count, point_count)
    image_sizes = np.array([1920.0, 1080.0, 1920.0, 1080.0], dtype=np.float64)
    return correspondences, image_sizes, known_inliers, expected


def test_public_api_is_available() -> None:
    for name in (
        "estimateHomography",
        "RANSACSettings",
        "ScoringType",
        "SamplerType",
        "LocalOptimizationType",
        "NeighborhoodType",
    ):
        assert hasattr(pysuperansac, name)


def test_gcransac_homography_estimation() -> None:
    correspondences, image_sizes, known_inliers = synthetic_homography_case()

    homography, inlier_indices, score, iterations = pysuperansac.estimateHomography(
        correspondences,
        image_sizes,
        None,
        gcransac_settings(),
    )

    homography = np.asarray(homography, dtype=np.float64)
    assert homography.shape == (3, 3)
    assert np.isfinite(homography).all()
    assert np.isfinite(score)
    assert 0 < iterations <= 500
    assert len(inlier_indices) >= int(0.7 * known_inliers.size)
    assert all(0 <= index < correspondences.shape[0] for index in inlier_indices)

    homography /= homography[2, 2]
    source = np.column_stack((correspondences[known_inliers, :2], np.ones(known_inliers.size)))
    projected = source @ homography.T
    projected = projected[:, :2] / projected[:, 2:]
    error = np.linalg.norm(projected - correspondences[known_inliers, 2:4], axis=1)
    assert np.median(error) < 0.5
    assert np.percentile(error, 95) < 1.0


def test_gcransac_local_optimization_uses_selected_inliers() -> None:
    correspondences, image_sizes, known_inliers, expected = adversarial_gcransac_case()
    settings = gcransac_settings()
    settings.min_iterations = 300
    settings.max_iterations = 300
    settings.local_opt_k = 3
    settings.final_optimization = pysuperansac.LocalOptimizationType.Nothing
    settings.homography_bundle_refinement = False

    homography, inlier_indices, _, _ = pysuperansac.estimateHomography(
        correspondences,
        image_sizes,
        None,
        settings,
    )

    selected = np.zeros(correspondences.shape[0], dtype=bool)
    selected[np.asarray(inlier_indices, dtype=np.int64)] = True
    assert selected[known_inliers].mean() >= 0.8

    homography = np.asarray(homography, dtype=np.float64)
    homography /= homography[2, 2]
    source = np.column_stack((correspondences[known_inliers, :2], np.ones(known_inliers.size)))
    projected = source @ homography.T
    projected = projected[:, :2] / projected[:, 2:]
    expected_projection = source @ expected.T
    expected_projection = expected_projection[:, :2] / expected_projection[:, 2:]
    rmse = np.sqrt(np.mean(np.sum((projected - expected_projection) ** 2, axis=1)))
    assert rmse < 0.8


@pytest.mark.parametrize(
    "correspondences,image_sizes",
    [
        (np.empty((0, 4), dtype=np.float64), np.ones(4, dtype=np.float64)),
        (np.empty((4, 3), dtype=np.float64), np.ones(4, dtype=np.float64)),
        (np.empty((4, 4), dtype=np.float64), np.ones(3, dtype=np.float64)),
        (np.empty(16, dtype=np.float64), np.ones(4, dtype=np.float64)),
    ],
)
def test_invalid_inputs_raise_python_exception(
    correspondences: np.ndarray,
    image_sizes: np.ndarray,
) -> None:
    with pytest.raises((RuntimeError, ValueError)):
        pysuperansac.estimateHomography(correspondences, image_sizes)
