#!/usr/bin/env bash
# Download the public TDC ADMET benchmark files (Harvard Dataverse) used to train mockgen's value models.
# Files land in data/public/ (gitignored). Records are never copied into the archive.
set -euo pipefail
cd "$(dirname "$0")/../data" && mkdir -p public && cd public
for pair in herg:4259588 herg_karim:6822246 cyp1a2_veith:4259573 cyp2c9_veith:4259577 cyp2c19_veith:4259576 \
            cyp2d6_veith:4259580 cyp3a4_veith:4259582 clearance_microsome_az:4266186 clearance_hepatocyte_az:4266187 \
            caco2_wang:4259569 solubility_aqsoldb:4259610 ppbr_az:6413140 lipophilicity_astrazeneca:4259595; do
  n=${pair%%:*}; id=${pair##*:}
  [ -s "$n.tab" ] || curl -sL --max-time 120 -o "$n.tab" "https://dataverse.harvard.edu/api/access/datafile/$id"
  echo "$n $(wc -l < "$n.tab") lines"
done
