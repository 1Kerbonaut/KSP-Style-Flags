from pathlib import Path
import subprocess

source_dir = Path(r"D:\GitHub\KSP Style Flag\UT Maps")
output_dir = Path(r"D:\GitHub\KSP Style Flag\UT Maps\Non Font Dependent")

inkscape_exe = r"C:\Program Files\Inkscape\bin\inkscape.exe"

for svg in source_dir.rglob("*.svg"):
    relative = svg.relative_to(source_dir)
    output = output_dir / relative
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"Converting: {relative}")

    subprocess.run([
        inkscape_exe,
        str(svg),
        "--export-text-to-path",
        "--export-plain-svg",
        f"--export-filename={output}",
    ], check=True)

print("Conversion complete.")