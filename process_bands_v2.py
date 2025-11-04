import json
import random

# Manually extract all band data by reading the file in chunks
with open('/nfs/kun2/users/mianw/CVPR/draw/recevied', 'r', encoding='utf-8') as f:
    content = f.read()

# Split by the pattern that separates JSON objects (}\n{)
parts = content.split('}\n\n{')

# Add back the braces
json_strings = []
for i, part in enumerate(parts):
    if i == 0:
        json_strings.append(part + '}')
    elif i == len(parts) - 1:
        json_strings.append('{' + part)
    else:
        json_strings.append('{' + part + '}')

# Parse each JSON string
all_bands = []
for i, json_str in enumerate(json_strings):
    try:
        obj = json.loads(json_str)
        if 'bands' in obj:
            num_bands = len(obj['bands'])
            print(f"✓ JSON block {i+1}: Parsed {num_bands} bands")
            all_bands.extend(obj['bands'])
            for band in obj['bands']:
                print(f"  - {band['name']}")
    except json.JSONDecodeError as e:
        print(f"✗ JSON block {i+1}: Failed to parse - {e}")
        # Try to diagnose the issue
        print(f"  First 100 chars: {json_str[:100]}")

print(f"\n{'='*80}")
print(f"Total bands collected: {len(all_bands)}")
print(f"{'='*80}\n")

# List all bands
expected_bands = ["Polyphia", "Eagles", "Nirvana", "Sleep Token", "Dream Theater",
                  "Tool", "Opeth", "Haken", "Between the Buried and Me", "Symphony X",
                  "Queensrÿche", "Fates Warning", "Jinjer", "Blood Incantation", "OU",
                  "Caligula's Horse", "Dvne", "Hand of Juno", "Chat Pile", "Ghost"]

collected_names = [b['name'] for b in all_bands]
missing = [name for name in expected_bands if name not in collected_names]

if missing:
    print(f"⚠️  Missing bands: {', '.join(missing)}")
else:
    print("✓ All expected bands collected!")

# Process each band: randomly select 1 song from the 5 available
processed_bands = []
images_to_collect = []

random.seed(42)  # For reproducibility

for band in all_bands:
    if 'recommendedSongs' in band and len(band['recommendedSongs']) > 0:
        selected_song = random.choice(band['recommendedSongs'])

        def sanitize_filename(name):
            name = str(name).lower()
            replacements = {
                'ÿ': 'y', ':': '', '(': '', ')': '', '[': '', ']': '',
                '\'': '', '"': '', '.': '', ',': '', '&': 'and',
                ' ': '_', '/': '_', '\\': '_'
            }
            for old, new in replacements.items():
                name = name.replace(old, new)
            # Remove multiple underscores
            while '__' in name:
                name = name.replace('__', '_')
            return name[:80].strip('_')

        band_filename = sanitize_filename(band['name'])
        song_filename = sanitize_filename(selected_song['title'])

        processed_band = {
            "name": band['name'],
            "bio": band['bio'],
            "bandImage": f"images/bands/{band_filename}.jpg",
            "recommendedSong": {
                "title": selected_song['title'],
                "review": selected_song['review'],
                "albumCover": f"images/albums/{band_filename}_{song_filename}.jpg"
            }
        }

        processed_bands.append(processed_band)

        images_to_collect.append({
            "type": "band_image",
            "band": band['name'],
            "filename": f"{band_filename}.jpg",
            "path": processed_band['bandImage'],
            "search_query": f"{band['name']} band photo"
        })

        images_to_collect.append({
            "type": "album_cover",
            "band": band['name'],
            "song": selected_song['title'],
            "filename": f"{band_filename}_{song_filename}.jpg",
            "path": processed_band['recommendedSong']['albumCover'],
            "search_query": f"{band['name']} {selected_song['title']} album cover"
        })

# Save processed JSON
final_json = {"bands": processed_bands}
output_path = '/nfs/kun2/users/mianw/mianwu01.github.io/bands_data.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(final_json, f, indent=2, ensure_ascii=False)

print(f"\n✅ Processed data saved to: {output_path}")
print(f"   Total bands: {len(processed_bands)}")

# Save image collection list
images_path = '/nfs/kun2/users/mianw/mianwu01.github.io/images_to_collect.json'
with open(images_path, 'w', encoding='utf-8') as f:
    json.dump(images_to_collect, f, indent=2, ensure_ascii=False)

print(f"\n✅ Image collection list saved to: {images_path}")
print(f"   Total images: {len(images_to_collect)} ({len(images_to_collect)//2} bands × 2)")

# Create a markdown checklist for image collection
checklist_path = '/nfs/kun2/users/mianw/mianwu01.github.io/images_checklist.md'
with open(checklist_path, 'w', encoding='utf-8') as f:
    f.write("# Band Images & Album Covers Collection Checklist\n\n")
    f.write(f"Total: {len(processed_bands)} bands, {len(images_to_collect)} images\n\n")
    f.write("## Instructions\n")
    f.write("1. Create directories: `mkdir -p images/bands images/albums`\n")
    f.write("2. Download images using the search queries below\n")
    f.write("3. Save each image with the exact filename specified\n\n")
    f.write("---\n\n")

    for i, band in enumerate(processed_bands, 1):
        f.write(f"## {i}. {band['name']}\n\n")
        f.write(f"**Selected Song:** {band['recommendedSong']['title']}\n\n")
        f.write(f"### Band Image\n")
        f.write(f"- [ ] **Search:** `{band['name']} band photo`\n")
        f.write(f"- **Save as:** `{band['bandImage']}`\n\n")
        f.write(f"### Album Cover\n")
        f.write(f"- [ ] **Search:** `{band['name']} {band['recommendedSong']['title']} album cover`\n")
        f.write(f"- **Save as:** `{band['recommendedSong']['albumCover']}`\n\n")
        f.write("---\n\n")

print(f"\n✅ Image checklist saved to: {checklist_path}")

# Print summary
print(f"\n{'='*80}")
print("SELECTED SONGS SUMMARY")
print(f"{'='*80}\n")
for i, band in enumerate(processed_bands, 1):
    print(f"{i:2d}. {band['name']:30s} → {band['recommendedSong']['title']}")
