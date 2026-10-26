#!/usr/bin/env bash
set -euo pipefail
# Read-only offline regression. No client install, no network or cache mutation.
if [[ $# -ne 2 ]]; then
  echo 'Usage: run_r267_linux.sh /path/to/R265_PRIVATE.zip /path/to/.spawnpk.zip' >&2
  exit 2
fi
R265=$(realpath "$1")
ASSETS=$(realpath "$2")
EXPECTED_R265='9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb'
EXPECTED_ASSETS='8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565'
EXPECTED_JAR='dc42ce52380d51bbc6162589d66e7226e5c86541ab84869f710b38ceffd7a503'
sha(){ sha256sum "$1" | cut -d' ' -f1; }
[[ -f "$R265" && "$(sha "$R265")" == "$EXPECTED_R265" ]] || { echo 'R265 private ZIP SHA256 mismatch' >&2; exit 3; }
[[ -f "$ASSETS" && "$(sha "$ASSETS")" == "$EXPECTED_ASSETS" ]] || { echo 'private asset ZIP SHA256 mismatch' >&2; exit 4; }
DIR=$(cd "$(dirname "$0")" && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
unzip -q "$R265" -d "$WORK/r265"
JAR="$WORK/r265/evidence/R265_UNIFIED_SOURCE_BUILT.jar"
[[ "$(sha "$JAR")" == "$EXPECTED_JAR" ]] || { echo 'R265 production JAR SHA256 mismatch' >&2; exit 5; }
LIB1="$WORK/r265/dependencies/R239_EXACT_RUNTIME_LIB.jar"
LIB2="$WORK/r265/dependencies/R218_EXACT_LIBS_COMPILE_ONLY_PRIVATE.jar"
CP="$JAR:$LIB1:$LIB2"
mkdir -p "$WORK/classes"
javac --release 11 -encoding UTF-8 -cp "$CP" -d "$WORK/classes" "$DIR/R267AuthenticKitRegression.java"
xvfb-run -a java -Djava.awt.headless=false -Xmx1000m -cp "$WORK/classes:$CP" R267AuthenticKitRegression "$ASSETS"
