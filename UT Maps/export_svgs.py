
import shutil
import subprocess
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "Exported_Images"

EXPORT_WIDTH = 2048
BACKGROUND_COLOR = "#000e25"
HIDDEN_LAYER = "Markers"

FLATPAK = shutil.which("flatpak")

if FLATPAK is None:
    raise FileNotFoundError("Flatpak was not found.")

INKSCAPE = [FLATPAK, "run", "org.inkscape.Inkscape"]

SVG_NS = "http://www.w3.org/2000/svg"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"

ET.register_namespace("", SVG_NS)
ET.register_namespace("inkscape", INKSCAPE_NS)

OUTPUT_DIR.mkdir(exist_ok=True)
svg_files = sorted(SCRIPT_DIR.glob("*.svg"))

if not svg_files:
    print("No SVG files found.")
    raise SystemExit(0)

for svg_file in svg_files:
    output_file = OUTPUT_DIR / f"{svg_file.stem}.png"
    temp_path = None

    try:
        tree = ET.parse(svg_file)
        root = tree.getroot()

        layer_found = False

        for element in root.iter():
            if (
                element.get(f"{{{INKSCAPE_NS}}}groupmode") == "layer"
                and element.get(f"{{{INKSCAPE_NS}}}label") == HIDDEN_LAYER
            ):
                styles = [
                    item.strip()
                    for item in element.get("style", "").split(";")
                    if item.strip()
                    and not item.strip().startswith("display:")
                ]
                styles.append("display:none")
                element.set("style", ";".join(styles))
                layer_found = True

        if not layer_found:
            print(
                f"Warning: '{HIDDEN_LAYER}' layer not found "
                f"in {svg_file.name}"
            )

        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".svg",
            prefix="_temp_export_",
            dir=SCRIPT_DIR,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        tree.write(
            temp_path,
            encoding="utf-8",
            xml_declaration=True,
        )

        command = [
            *INKSCAPE,
            str(temp_path),
            f"--export-filename={output_file}",
            f"--export-background={BACKGROUND_COLOR}",
            "--export-background-opacity=1",
        ]

        if EXPORT_WIDTH is not None:
            command.append(f"--export-width={EXPORT_WIDTH}")

        subprocess.run(command, check=True)

        print(f"Exported: {svg_file.name} -> {output_file.name}")

    except (ET.ParseError, OSError, subprocess.CalledProcessError) as error:
        print(f"Failed to export {svg_file.name}: {error}")

    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

print("Export finished.")
