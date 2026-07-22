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
