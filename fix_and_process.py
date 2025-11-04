import json
import random

# Read and fix the JSON file
with open('/nfs/kun2/users/mianw/CVPR/draw/recevied', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace smart quotes with standard quotes
# These are curly quotes that appear in the reviews
content_fixed = content.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")

print("Fixing smart quotes in JSON...")

# Now split into JSON objects
parts = content_fixed.split('}\n\n{')

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
            print(f"✓ Block {i+1}: {num_bands} bands")
            all_bands.extend(obj['bands'])
    except json.JSONDecodeError as e:
        print(f"✗ Block {i+1}: Parse error - {e}")

print(f"\n{'='*80}")
print(f"Total bands: {len(all_bands)}")
print(f"{'='*80}\n")

# Verify all expected bands
expected = ["Polyphia", "Eagles", "Nirvana", "Sleep Token", "Dream Theater",
            "Tool", "Opeth", "Haken", "Between the Buried and Me", "Symphony X",
            "Queensrÿche", "Fates Warning", "Jinjer", "Blood Incantation", "OU",
            "Caligula's Horse", "Dvne", "Hand of Juno", "Chat Pile", "Ghost"]

collected = [b['name'] for b in all_bands]
missing = [n for n in expected if n not in collected]

if missing:
    print(f"⚠️  Missing: {', '.join(missing)}\n")
else:
    print("✅ All 20 expected bands collected!\n")

# Process bands: select 1 random song per band
processed_bands = []
images_to_collect = []

random.seed(42)

for band in all_bands:
    if 'recommendedSongs' in band and band['recommendedSongs']:
        selected = random.choice(band['recommendedSongs'])

        def clean_filename(s):
            s = s.lower()
            chars = {
                'ÿ': 'y', ':': '', '(': '', ')': '', '[': '', ']': '',
                '\'': '', '"': '', '.': '', ',': '', '&': 'and',
                ' ': '_', '/': '_', '\\': '_', ''': '', ''': ''
            }
            for old, new in chars.items():
                s = s.replace(old, new)
            while '__' in s:
                s = s.replace('__', '_')
            return s[:80].strip('_')

        band_fn = clean_filename(band['name'])
        song_fn = clean_filename(selected['title'])

        processed = {
            "name": band['name'],
            "bio": band['bio'],
            "bandImage": f"images/bands/{band_fn}.jpg",
            "recommendedSong": {
                "title": selected['title'],
                "review": selected['review'],
                "albumCover": f"images/albums/{band_fn}_{song_fn}.jpg"
            }
        }

        processed_bands.append(processed)

        images_to_collect.extend([
            {
                "type": "band_image",
                "band": band['name'],
                "filename": f"{band_fn}.jpg",
                "path": processed['bandImage'],
                "search": f"{band['name']} band photo high quality"
            },
            {
                "type": "album_cover",
                "band": band['name'],
                "song": selected['title'],
                "filename": f"{band_fn}_{song_fn}.jpg",
                "path": processed['recommendedSong']['albumCover'],
                "search": f"{band['name']} {selected['title']} album cover"
            }
        ])

# Save JSON
out_json = '/nfs/kun2/users/mianw/mianwu01.github.io/bands_data.json'
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump({"bands": processed_bands}, f, indent=2, ensure_ascii=False)

out_images = '/nfs/kun2/users/mianw/mianwu01.github.io/images_to_collect.json'
with open(out_images, 'w', encoding='utf-8') as f:
    json.dump(images_to_collect, f, indent=2, ensure_ascii=False)

# Create markdown checklist
out_md = '/nfs/kun2/users/mianw/mianwu01.github.io/IMAGES_TODO.md'
with open(out_md, 'w', encoding='utf-8') as f:
    f.write("# 🎵 Band Images & Album Covers TODO\n\n")
    f.write(f"**Total:** {len(processed_bands)} bands, {len(images_to_collect)} images\n\n")
    f.write("## Setup\n```bash\n")
    f.write("cd /nfs/kun2/users/mianw/mianwu01.github.io\n")
    f.write("mkdir -p images/bands images/albums\n```\n\n")
    f.write("---\n\n")

    for i, band in enumerate(processed_bands, 1):
        f.write(f"## {i}. {band['name']}\n\n")
        f.write(f"**Song:** *{band['recommendedSong']['title']}*\n\n")

        band_img = [img for img in images_to_collect if img['band'] == band['name'] and img['type'] == 'band_image'][0]
        album_img = [img for img in images_to_collect if img['band'] == band['name'] and img['type'] == 'album_cover'][0]

        f.write(f"- [ ] **Band Photo**\n")
        f.write(f"  - Search: `{band_img['search']}`\n")
        f.write(f"  - Save as: `{band_img['path']}`\n\n")
        f.write(f"- [ ] **Album Cover**\n")
        f.write(f"  - Search: `{album_img['search']}`\n")
        f.write(f"  - Save as: `{album_img['path']}`\n\n")

print(f"✅ bands_data.json → {out_json}")
print(f"✅ images_to_collect.json → {out_images}")
print(f"✅ IMAGES_TODO.md → {out_md}")

print(f"\n{'='*80}")
print("SELECTED SONGS")
print(f"{'='*80}\n")
for i, b in enumerate(processed_bands, 1):
    print(f"{i:2d}. {b['name']:30s} → {b['recommendedSong']['title']}")
