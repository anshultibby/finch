"""
Compare different DataFrame serialization formats for size efficiency
"""
import pandas as pd
import json

# Sample insider trading data (6 fields from to_df_row)
sample_data = [
    {"date": "2025-10-24", "insider": "Law Lauren Kristen", "position": "Sub-Adviser", "type": "P-Purchase", "shares": 20000.0, "price": 5.007},
    {"date": "2025-10-23", "insider": "Bright Jill", "position": "director", "type": "P-Purchase", "shares": 400.0, "price": 65.95},
    {"date": "2025-10-23", "insider": "Smith John", "position": "CEO", "type": "P-Purchase", "shares": 10000.0, "price": 123.45},
    {"date": "2025-10-22", "insider": "Johnson Mary", "position": "CFO", "type": "S-Sale", "shares": 5000.0, "price": 98.76},
    {"date": "2025-10-21", "insider": "Williams Bob", "position": "officer", "type": "P-Purchase", "shares": 1500.0, "price": 234.56},
] * 20  # Multiply to simulate 100 trades

df = pd.DataFrame(sample_data)

print("="*80)
print("DataFrame Serialization Format Comparison")
print("="*80)
print(f"Number of rows: {len(df)}")
print(f"Number of columns: {len(df.columns)}\n")

# 1. Split format (current)
split_format = df.to_dict('split')
split_json = json.dumps(split_format)
print(f"1. SPLIT FORMAT (current)")
print(f"   Structure: {{'columns': [...], 'data': [[...], [...], ...]}}")
print(f"   Size: {len(split_json):,} characters ({len(split_json)/1024:.2f} KB)")
print(f"   Sample: {split_json[:150]}...\n")

# 2. Records format (list of dicts)
records_format = df.to_dict('records')
records_json = json.dumps(records_format)
print(f"2. RECORDS FORMAT")
print(f"   Structure: [{{'col1': val1, 'col2': val2}}, ...]")
print(f"   Size: {len(records_json):,} characters ({len(records_json)/1024:.2f} KB)")
print(f"   ⚠️  Repeats column names for EVERY row - INEFFICIENT")
print(f"   Sample: {records_json[:150]}...\n")

# 3. List format
list_format = df.to_dict('list')
list_json = json.dumps(list_format)
print(f"3. LIST FORMAT")
print(f"   Structure: {{'col1': [val1, val2, ...], 'col2': [val1, val2, ...]}}")
print(f"   Size: {len(list_json):,} characters ({len(list_json)/1024:.2f} KB)")
print(f"   Sample: {list_json[:150]}...\n")

# 4. CSV format
csv_format = df.to_csv(index=False)
print(f"4. CSV FORMAT ⭐")
print(f"   Structure: Plain CSV text with header row")
print(f"   Size: {len(csv_format):,} characters ({len(csv_format)/1024:.2f} KB)")
print(f"   ✅ Most compact - no JSON overhead!")
print(f"   Sample:\n{csv_format[:200]}...\n")

# 5. CSV as JSON string (what we'd actually send)
csv_json = json.dumps({"csv": csv_format})
print(f"5. CSV AS JSON STRING (what we'd send to LLM)")
print(f"   Structure: {{'csv': 'date,insider,...\\nval1,val2,...'}}")
print(f"   Size: {len(csv_json):,} characters ({len(csv_json)/1024:.2f} KB)")
print(f"   Sample: {csv_json[:150]}...\n")

# 6. TSV format (tab-separated, even more compact)
tsv_format = df.to_csv(index=False, sep='\t')
tsv_json = json.dumps({"tsv": tsv_format})
print(f"6. TSV FORMAT (tab-separated)")
print(f"   Structure: Tab-separated values")
print(f"   Size: {len(tsv_json):,} characters ({len(tsv_json)/1024:.2f} KB)")
print(f"   Sample: {tsv_json[:150]}...\n")

# Summary comparison
print("="*80)
print("SIZE COMPARISON SUMMARY")
print("="*80)

formats = [
    ("Split (current)", len(split_json)),
    ("Records", len(records_json)),
    ("List", len(list_json)),
    ("CSV raw", len(csv_format)),
    ("CSV as JSON", len(csv_json)),
    ("TSV as JSON", len(tsv_json)),
]

formats_sorted = sorted(formats, key=lambda x: x[1])

for i, (name, size) in enumerate(formats_sorted, 1):
    savings = ((formats[0][1] - size) / formats[0][1] * 100) if i > 1 else 0
    indicator = "🏆" if i == 1 else "✅" if i <= 2 else ""
    print(f"{i}. {indicator} {name:20s}: {size:6,} chars ({size/1024:5.2f} KB) ", end="")
    if savings > 0:
        print(f"[{savings:+.1f}% vs split]")
    else:
        print()

print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)
print("✅ Use CSV format wrapped in JSON: {'trades_csv': 'header\\nrow1\\nrow2...'}")
print("   - Most compact representation")
print("   - Easy for LLM to read and understand")
print("   - Standard format that LLMs are trained on")
print("   - Can include in prompt: 'Data is in CSV format'")
print("="*80)

