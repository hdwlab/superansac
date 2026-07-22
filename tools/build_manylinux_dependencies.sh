#!/usr/bin/env bash
set -euo pipefail

readonly project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly vcpkg_root=/opt/vcpkg
readonly installed_root=/opt/vcpkg_installed
readonly config_root=/opt/superansac-manylinux
readonly binary_cache=/opt/vcpkg-cache
readonly vcpkg_commit=cd61e1e26a038e82d6550a3ebbe0fbbfe7da78e3

dnf install -y curl git tar unzip zip
dnf clean all

if [[ ! -d "${vcpkg_root}/.git" ]]; then
  git clone https://github.com/microsoft/vcpkg.git "${vcpkg_root}"
fi
git -C "${vcpkg_root}" checkout --detach "${vcpkg_commit}"
"${vcpkg_root}/bootstrap-vcpkg.sh" -disableMetrics

rm -rf "${config_root}"
mkdir -p \
  "${config_root}/triplets" \
  "${config_root}/packaging/opencv-build-info" \
  "${binary_cache}"
cp "${project_root}/triplets/x64-linux-static-release.cmake" \
  "${config_root}/triplets/"
cp "${project_root}/packaging/opencv-build-info/"* \
  "${config_root}/packaging/opencv-build-info/"

export VCPKG_DEFAULT_BINARY_CACHE="${binary_cache}"
export VCPKG_DISABLE_METRICS=1
"${vcpkg_root}/vcpkg" install \
  --x-manifest-root="${project_root}" \
  --x-install-root="${installed_root}" \
  --triplet=x64-linux-static-release \
  --overlay-triplets="${config_root}/triplets"

test -f "${installed_root}/x64-linux-static-release/share/eigen3/Eigen3Config.cmake"
test -f "${installed_root}/x64-linux-static-release/share/opencv4/OpenCVConfig.cmake"
