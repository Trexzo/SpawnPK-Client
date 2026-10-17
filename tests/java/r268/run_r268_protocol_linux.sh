#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo 'Usage: bash run_r268_protocol_linux.sh /path/to/R265_PRIVATE.zip' >&2
  exit 2
fi
R265=$(realpath "$1")
EXPECTED='9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb'
EXPECTED_JAR='dc42ce52380d51bbc6162589d66e7226e5c86541ab84869f710b38ceffd7a503'
sha(){ sha256sum "$1" | cut -d' ' -f1; }
[[ "$(sha "$R265")" == "$EXPECTED" ]] || { echo 'R265 ZIP checksum mismatch' >&2; exit 3; }
DIR=$(cd "$(dirname "$0")" && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
unzip -q "$R265" -d "$WORK"
J="$WORK/evidence/R265_UNIFIED_SOURCE_BUILT.jar"
[[ "$(sha "$J")" == "$EXPECTED_JAR" ]] || { echo 'R265 production JAR SHA mismatch' >&2; exit 4; }
LIB1="$WORK/dependencies/R239_EXACT_RUNTIME_LIB.jar"
LIB2="$WORK/dependencies/R218_EXACT_LIBS_COMPILE_ONLY_PRIVATE.jar"
CP="$J:$LIB1:$LIB2"
mkdir -p "$WORK/classes"
javac --release 11 -encoding UTF-8 -cp "$CP" -d "$WORK/classes" "$DIR/R268TeleportAppearanceRegression.java"
xvfb-run -a java -Djava.awt.headless=false -cp "$WORK/classes:$CP" R268TeleportAppearanceRegression
