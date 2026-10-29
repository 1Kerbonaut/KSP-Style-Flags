
import shutil
import subprocess
from pathlib import Path

# Folder containing this script and the SVG files
SCRIPT_DIR = Path(__file__).resolve().parent

# Output settings
OUTPUT_DIR = SCRIPT_DIR / "Exported_Images"
EXPORT_WIDTH = None  # Set to e.g. 2000 for a fixed pixel width

# Find Inkscape
INKSCAPE = shutil.which("inkscape")

if INKSCAPE is None:
    raise FileNotFoundError(
        "Inkscape was not found. Make sure it is installed "
        "and available in your system PATH."
    )

# Create the output folder if it does not exist
OUTPUT_DIR.mkdir(exist_ok=True)

# Find SVG files directly in the script folder (no subfolders)
svg_files = sorted(SCRIPT_DIR.glob("*.svg"))

if not svg_files:
    print("No SVG files found.")
    raise SystemExit(0)

# Export each SVG as a PNG
for svg_file in svg_files:
    output_file = OUTPUT_DIR / f"{svg_file.stem}.png"

    command = [
        INKSCAPE,
        str(svg_file),
        f"--export-filename={output_file}",
    ]

    if EXPORT_WIDTH is not None:
        command.append(f"--export-width={EXPORT_WIDTH}")

    try:
        subprocess.run(command, check=True)
        print(f"Exported: {svg_file.name} -> {output_file.name}")

    except subprocess.CalledProcessError as error:
        print(f"Failed to export {svg_file.name}: {error}")

print("Export finished.")