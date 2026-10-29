import shutil
import subprocess
import tempfile
import platform
from pathlib import Path
import xml.etree.ElementTree as ET

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "Export"

SYSTEM = platform.system()

SVG_NS = "http://www.w3.org/2000/svg"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"

EXPORT_WIDTH = 2048
BACKGROUND_COLOR = "#000e25"
HIDDEN_LAYER = "Markers"

if SYSTEM == "Windows":
    # Search for Inkscape in the Windows PATH
    inkscape_path = shutil.which("inkscape")

    # Fall back to the default installation location
    if inkscape_path is None:
        default_path = (
            Path("C:/Program Files/Inkscape/bin/inkscape.exe")
        )
        if default_path.exists():
            inkscape_path = str(default_path)

    if inkscape_path is None:
        raise FileNotFoundError(
            "Inkscape was not found. Add it to PATH or "
            "check its installation directory."
        )

    INKSCAPE = [inkscape_path]

elif SYSTEM == "Linux":
    # Prefer Flatpak, as used on your Mint system
    flatpak_path = shutil.which("flatpak")

    if flatpak_path is not None:
        INKSCAPE = [
            flatpak_path,
            "run",
            "org.inkscape.Inkscape",
        ]
    else:
        inkscape_path = shutil.which("inkscape")

        if inkscape_path is None:
            raise FileNotFoundError(
                "Neither Flatpak Inkscape nor a native "
                "Inkscape installation was found."
            )

        INKSCAPE = [inkscape_path]

else:
    raise OSError(f"Unsupported operating system: {SYSTEM}")

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
            # background, comment for transparent mode
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
