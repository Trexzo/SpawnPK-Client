#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 3 ]];then
  echo 'Usage: bash run_r282_linux.sh R278_PRIVATE.zip R265_PRIVATE.zip ".spawnpk (4).zip"' >&2;exit 2
fi
DIR=$(cd "$(dirname "$0")/.." && pwd)
OUT=$(mktemp -d -t spawnpk-r282.XXXXXXXX)
trap 'rm -rf "$OUT"' EXIT
python3 "$DIR/scripts/stage_r278_inputs.py" "$1" "$2" "$3" "$OUT"
CP="$OUT/R278_SOURCE_BUILT_CLASS_ONLY.jar:$OUT/R239_EXACT_RUNTIME_LIB.jar:$OUT/R218_EXACT_LIBS_COMPILE_ONLY_PRIVATE.jar"
mkdir -p "$OUT/tests"
javac --release 11 -encoding UTF-8 -cp "$CP" -d "$OUT/tests" "$DIR/tests/R282DefinitionBankIsolationRegression.java"
java -Djava.awt.headless=true "-Duser.home=$OUT/home" -cp "$OUT/tests:$CP" R282DefinitionBankIsolationRegression "$OUT/config.bin"
echo 'R282_CLEAN_PINNED_OWNER_SOURCE_BANK_REGRESSION_PASS checks=78'
