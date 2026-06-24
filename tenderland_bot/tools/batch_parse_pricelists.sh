#!/bin/bash
# Batch parser for all Glüvex 1С XLSX pricelists.
# Usage: ./tools/batch_parse_pricelists.sh <input_xlsx_dir> <output_json_dir>

set -euo pipefail

INPUT_DIR="${1:-./pricelists_xlsx}"
OUTPUT_DIR="${2:-./pricelists_json}"

if [ ! -d "$INPUT_DIR" ]; then
    echo "ERROR: Input dir not found: $INPUT_DIR" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "=== Batch parsing XLSX pricelists ==="
echo "Input:  $INPUT_DIR"
echo "Output: $OUTPUT_DIR"
echo ""

count=0
errors=0
for xlsx in "$INPUT_DIR"/*.xlsx; do
    [ -e "$xlsx" ] || continue
    filename=$(basename "$xlsx" .xlsx)
    # Sanitize filename for output JSON
    safe_name=$(echo "$filename" | tr ' ' '_' | tr -cd '[:alnum:]_-')
    output="$OUTPUT_DIR/${safe_name}.json"

    echo "→ $filename"
    if PYTHONIOENCODING=utf-8 python tools/parse_pricelist_xlsx.py "$xlsx" -o "$output" --distributor-override "Glüvex" 2>&1 | tail -20; then
        count=$((count + 1))
        echo ""
    else
        errors=$((errors + 1))
        echo "  FAILED" >&2
    fi
done

echo "=== Done: $count parsed, $errors errors ==="
