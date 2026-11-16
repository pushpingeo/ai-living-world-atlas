#!/usr/bin/env bash
# Fetch every published wave (runs/published.txt) and every tags-* branch, then combine them into /tmp/pub.
set -euo pipefail
mkdir -p /tmp/waves /tmp/pub
DS=(); LY=(); TG=()
while read -r b; do
  [ -z "$b" ] && continue
  case "$b" in \#*) continue;; esac
  if git fetch -q origin "results/$b" 2>/dev/null; then
    # a wave that produced nothing (e.g. a diagnostic run) has no parquet files; skip it rather than fail
    if python -m atlas.parts get FETCH_HEAD datasets "/tmp/waves/$b.datasets.parquet" \
       && python -m atlas.parts get FETCH_HEAD layers "/tmp/waves/$b.layers.parquet"; then
      DS+=("/tmp/waves/$b.datasets.parquet"); LY+=("/tmp/waves/$b.layers.parquet")
    else echo "$b: no data yet, skipped" >&2; continue; fi
    echo "$b: $(git show FETCH_HEAD:RUN.txt)" >> /tmp/pub/SOURCES.txt
  fi
done < runs/published.txt
for b in $(git ls-remote --heads origin 'results/tags-*' | awk '{print $2}' | sed 's#refs/heads/##'); do
  git fetch -q origin "$b" && git show FETCH_HEAD:tags.parquet > "/tmp/waves/$(basename $b).tags.parquet" 2>/dev/null && TG+=("/tmp/waves/$(basename $b).tags.parquet") || true
done
python -m atlas.combine "${DS[@]}" --layers "${LY[@]}" ${TG[@]:+--tags "${TG[@]}"} --out /tmp/pub --only-passing  # the viewer and MCP carry passing datasets only; the full index stays in the wave files
