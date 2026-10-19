#!/usr/bin/env bash
set -euo pipefail
if [[ "$#" -ne 3 ]]; then echo 'Usage: run_r283_linux.sh R278_PRIVATE.zip R265_PRIVATE.zip SPAWNPK_ASSET.zip' >&2; exit 2; fi
ROOT=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d -t spawnpk-r283.XXXXXXXX)
trap 'rm -rf "$TMP"' EXIT
python3 "$ROOT/stage_r278_inputs.py" "$1" "$2" "$3" "$TMP"
CP="$TMP/R278_SOURCE_BUILT_CLASS_ONLY.jar:$TMP/R239_EXACT_RUNTIME_LIB.jar:$TMP/R218_EXACT_LIBS_COMPILE_ONLY_PRIVATE.jar"
mkdir -p "$TMP/classes"
javac --release 11 -encoding UTF-8 -cp "$CP" -d "$TMP/classes" "$ROOT/R283RegionBankSelectionRegression.java"
xvfb-run -a java -Djava.awt.headless=false "-Duser.home=$TMP/home" -cp "$TMP/classes:$CP" R283RegionBankSelectionRegression "$TMP/config.bin"
echo 'R283_CLEAN_OWNER_INPUT_REGION_SELECTOR_PASS checks=35'
