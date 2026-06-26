#!/usr/bin/env bash
# Run SiteFinder across a matrix of categories x districts.
# Results land in results/<category>/district_NN/{leads.csv,report.txt}.
#
# Usage:
#   scripts/run_matrix.sh "dentist hair_salon restaurant cafe barber physiotherapist" "1 6 7 8 15"
#   scripts/run_matrix.sh            # uses the defaults below
#
# Append --enrich places to ENRICH_ARGS to add Google ratings (needs an API key).
set -euo pipefail

CATEGORIES=${1:-"dentist hair_salon restaurant cafe barber physiotherapist"}
DISTRICTS=${2:-"1 6 7 8 15"}
# Discovery-only matrix by default (fast, free). Set EXTRA_ARGS="--audit" to also audit each cell,
# or run `sitefinder run` per segment for the full discovery+enrich+audit workflow.
EXTRA_ARGS=${EXTRA_ARGS:-"--no-enrich --no-audit"}

for category in $CATEGORIES; do
  for district in $DISTRICTS; do
    echo ">>> $category / district $district"
    sitefinder run --district "$district" --category "$category" $EXTRA_ARGS || {
      echo "    (failed for $category d$district; continuing)"
    }
  done
done

echo "Done. Compare runs under results/."
