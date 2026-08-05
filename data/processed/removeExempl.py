import json

input_file = 'data/processed/qSet_filtered.jsonl'
output_file = 'data/processed/qSet_filtered_noExempl.jsonl'

with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
    for line in infile:
        try:
            data = json.loads(line)
            if data.get("source_layer") != "exemplary_plan":
                outfile.write(line)
        except json.JSONDecodeError:
            continue