#!/usr/bin/env bash
set -euo pipefail

cd /src/watchdog
# Bundle actual Watchdog sources and Linux tools needed by validation. The
# upstream Python compiler bundles interpreter/native libraries for base-runner.
declare -a resources=(
    --add-data 'service-watchdog.sh:watchdog'
    --add-data 'VERSION:watchdog'
    --add-data 'lib/watchdog:watchdog/lib/watchdog'
    --add-data '.clusterfuzzlite/bridge.sh:watchdog'
)
for tool in bash yq base64 curl flock timeout date dirname mktemp tail tr mv env awk df hostname find; do
    tool_path="$(command -v "$tool")"
    resources+=(--add-binary "${tool_path}:bin")
done
compile_python_fuzzer .clusterfuzzlite/watchdog_fuzzer.py "${resources[@]}"
cp .clusterfuzzlite/watchdog_fuzzer.options "$OUT/"
zip -j "$OUT/watchdog_fuzzer_seed_corpus.zip" .clusterfuzzlite/corpus/*
