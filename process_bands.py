import json
import random
import re

# Read the file with multiple JSON objects
with open('/nfs/kun2/users/mianw/CVPR/draw/recevied', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all JSON objects that start with { and end with }
# Use regex to find all complete JSON objects
json_pattern = r'\{[^\{\}]*"bands"[^\{\}]*:\s*\[[^\]]*(?:\{[^\}]*\}[^\]]*)*\][^\{\}]*\}'

# More robust approach: split by newlines and reconstruct JSON objects
lines = content.split('\n')
current_obj = []
json_objects = []
brace_depth = 0

for line in lines:
    for char in line:
        if char == '{':
            brace_depth += 1
        elif char == '}':
            brace_depth -= 1

    current_obj.append(line)

    if brace_depth == 0 and current_obj:
        obj_str = '\n'.join(current_obj).strip()
        if obj_str:
            try:
                obj = json.loads(obj_str)
                if 'bands' in obj:
                    json_objects.append(obj)
                    print(f"✓ Parsed JSON object with {len(obj['bands'])} bands")
            except json.JSONDecodeError as e:
                print(f"✗ Failed to parse: {e}")
        current_obj = []

print(f"\nTotal JSON objects parsed: {len(json_objects)}")

# Merge all bands from all JSON objects
all_bands = []
for obj in json_objects:
    if 'bands' in obj:
        all_bands.extend(obj['bands'])

print(f"Total bands found: {len(all_bands)}")
print("\nBands list:")
for i, band in enumerate(all_bands, 1):
    print(f"{i}. {band['name']}")

# Process each band: randomly select 1 song from the 5 available
processed_bands = []
images_to_collect = []

random.seed(42)  # For reproducibility, you can remove this for true randomness

for band in all_bands:
    # Randomly select one song
    if 'recommendedSongs' in band and len(band['recommendedSongs']) > 0:
        selected_song = random.choice(band['recommendedSongs'])

        # Create sanitized filename
        def sanitize_filename(name):
            # Replace special characters
            name = name.lower()
            name = name.replace('ÿ', 'y')
            name = name.replace(':', '')
            name = name.replace('(', '')
            name = name.replace(')', '')
            name = name.replace('[', '')
            name = name.replace(']', '')
            name = name.replace('\'', '')
            name = name.replace('"', '')
            name = name.replace('.', '')
            name = name.replace(',', '')
            name = name.replace(' ', '_')
            name = name.replace('&', 'and')
            return name[:80]  # Limit length

        band_filename = sanitize_filename(band['name'])
        song_filename = sanitize_filename(selected_song['title'])

        # Create new band entry with single song
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

        # Add to collection list
        images_to_collect.append({
            "type": "band_image",
            "band": band['name'],
            "path": processed_band['bandImage'],
            "search_query": f"{band['name']} band photo"
        })

        images_to_collect.append({
            "type": "album_cover",
            "band": band['name'],
            "song": selected_song['title'],
            "path": processed_band['recommendedSong']['albumCover'],
            "search_query": f"{band['name']} {selected_song['title']} album cover"
        })

# Create final JSON structure
final_json = {
    "bands": processed_bands
}

# Save processed JSON
output_path = '/nfs/kun2/users/mianw/mianwu01.github.io/bands_data.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(final_json, f, indent=2, ensure_ascii=False)

print(f"\n✅ Processed data saved to: {output_path}")
print(f"Total bands processed: {len(processed_bands)}")

# Save image collection list
images_path = '/nfs/kun2/users/mianw/mianwu01.github.io/images_to_collect.json'
with open(images_path, 'w', encoding='utf-8') as f:
    json.dump(images_to_collect, f, indent=2, ensure_ascii=False)

print(f"\n✅ Image collection list saved to: {images_path}")
print(f"Total images to collect: {len(images_to_collect)}")

# Print summary
print("\n" + "="*80)
print("SUMMARY - Selected Songs by Band:")
print("="*80)
for i, band in enumerate(processed_bands, 1):
    print(f"\n{i}. 🎵 {band['name']}")
    print(f"   📀 Song: {band['recommendedSong']['title']}")
