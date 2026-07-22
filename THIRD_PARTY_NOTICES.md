# Third-party notices

The `pysuperansac` binary distribution contains or links code from the
projects below. The corresponding complete license texts are included in the
`THIRD_PARTY_LICENSES` directory and in the wheel's `.dist-info/licenses`
directory.

| Component | Copyright / attribution | License |
| --- | --- | --- |
| Fork packaging and binary-energy implementation | Copyright 2026 Human Dataware Lab. Co., Ltd. | MIT |
| SupeRANSAC sources contributed by ETH Zurich and CTU | Copyright 2024 ETH Zurich and respective contributors | BSD-3-Clause |
| PoseLib numerical optimization sources | Copyright 2020-2021 Viktor Larsson and contributors | BSD-3-Clause |
| nanoflann | Copyright 2008-2009 Marius Muja and David G. Lowe; 2011-2024 Jose Luis Blanco | BSD-2-Clause |
| pybind11 | Copyright 2016 Wenzel Jakob and contributors | BSD-3-Clause |
| Eigen | Copyright Benoit Jacob, Gael Guennebaud, and contributors | MPL-2.0 |
| OpenCV | Copyright OpenCV contributors | Apache-2.0 |
| zlib / zlib-ng, when selected by the resolved OpenCV build | Copyright Jean-loup Gailly, Mark Adler, and contributors | Zlib |

SupeRANSAC and Graph-Cut RANSAC are academic algorithms. Please retain the
paper citations documented in the project README when publishing results.

The research-only `GCoptimization`, `energy`, and legacy Boykov-Kolmogorov
source bundle used by earlier fork releases is not included in this source
revision or in wheels built from it. Binary energy minimization is implemented
in-tree under the project's MIT license.
