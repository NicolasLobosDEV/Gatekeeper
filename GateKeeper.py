import os
import subprocess
import soundfile as sf
import pandas as pd
import csv
from mutagen import File

# === CONFIG ===
print(r"Folder path example for Windows:\nC:\\Users\\nlobo\\Music\\Uber Voice\n")
print(r"Folder path example for MacOS:\n/Users/<your_username>/Uber_Voice\n")
folder_path = input("Enter the full folder path: ").strip()
folder_path = os.path.abspath(os.path.expanduser(folder_path))
output_folder = os.path.join(folder_path, "to_upload")
target_lufs = -20.0  # Target LUFS (integrated loudness)
true_peak_limit = -1.0  # True peak limit in dB
output_csv = os.path.join(output_folder,'combined_audio_report.csv')  # Final report
file_extensions = '.flac'

# === Ensure output folder exists ===
os.makedirs(output_folder, exist_ok=True)

combined_results = []
total_duration_seconds = 0.0

for filename in os.listdir(folder_path):
    if filename.lower().endswith(file_extensions):
        input_path = os.path.join(folder_path, filename)
        output_path = os.path.join(output_folder, f"normalized_{filename}")

        print(f"🔄 Normalizing: {filename}")

        # Normalize audio with ffmpeg
        try:
            cmd = [
                'ffmpeg', '-i', input_path,
                '-filter_complex', f'loudnorm=I={target_lufs}:TP={true_peak_limit}:LRA=11',
                '-ac', '1',  # Mono output
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            print(f"❌ FFmpeg error with {filename}: {e}")
            continue

        # Load audio file info
        try:
            info = sf.info(output_path)
            duration_sec = info.frames / info.samplerate
            total_duration_seconds += duration_sec
            file_size_bytes = os.path.getsize(output_path)
            bitrate_kbps = (file_size_bytes * 8 / duration_sec) / 1000
        except Exception as e:
            print(f"❌ SoundFile error with {filename}: {e}")
            continue

        # Load metadata using mutagen
        audio = File(output_path, easy=False)
        if audio is None or audio.tags is None or not hasattr(audio, 'info'):
            tags = {}
        else:
            tags = {key: ", ".join(map(str, val)) if isinstance(val, list) else str(val)
                    for key, val in audio.tags.items()}

        # Append all data to results
        tags.update({
            'filename': filename,
            'normalized_lufs': target_lufs,
            'true_peak_limit_db': true_peak_limit,
            'duration_sec': round(duration_sec, 2),
            'bitrate_kbps': round(bitrate_kbps, 2),
            'samplerate': info.samplerate,
            'channels': info.channels,
            'format': info.format
        })
        combined_results.append(tags)

# === Collect all headers for CSV ===
all_keys = set()
for item in combined_results:
    all_keys.update(item.keys())
all_keys = sorted(all_keys)

# === Write combined report ===
with open(output_csv, "w", encoding="utf-8", newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=all_keys)
    writer.writeheader()
    for row in combined_results:
        writer.writerow(row)

# === Print total duration ===
total_minutes = int(total_duration_seconds) // 60
total_seconds = int(total_duration_seconds) % 60
print(f"\n✅ Done! Report saved to {output_csv}")
print(f"🎧 Total audio duration: {total_minutes} min {total_seconds} sec")
