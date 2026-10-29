import json
import math
import re
from pathlib import Path

from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"

def local_name(element):
    return etree.QName(element).localname

def parse_transform(transform):
    """Parse an SVG transform list into a 2D affine matrix."""
    result = (1, 0, 0, 1, 0, 0)

    for name, args in re.findall(
        r"([a-zA-Z]+)\s*\(([^)]*)\)", transform or ""
    ):
        nums = [
            float(x)
            for x in re.findall(
                r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?",
                args,
            )
        ]

        if name == "matrix" and len(nums) == 6:
            m = tuple(nums)

        elif name == "translate" and nums:
            tx = nums[0]
            ty = nums[1] if len(nums) > 1 else 0
            m = (1, 0, 0, 1, tx, ty)

        elif name == "scale" and nums:
            sx = nums[0]
            sy = nums[1] if len(nums) > 1 else sx
            m = (sx, 0, 0, sy, 0, 0)

        elif name == "rotate" and nums:
            angle = math.radians(nums[0])
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            rotation = (cos_a, sin_a, -sin_a, cos_a, 0, 0)

            if len(nums) >= 3:
                cx, cy = nums[1:3]
                m = multiply(
                    multiply(
                        (1, 0, 0, 1, cx, cy),
                        rotation,
                    ),
                    (1, 0, 0, 1, -cx, -cy),
                )
            else:
                m = rotation

        elif name == "skewX" and nums:
            m = (
                1, 0,
                math.tan(math.radians(nums[0])), 1,
                0, 0,
            )

        elif name == "skewY" and nums:
            m = (
                1, math.tan(math.radians(nums[0])),
                0, 1, 0, 0,
            )

        else:
            continue

        result = multiply(result, m)

    return result

def multiply(m1, m2):
    a, b, c, d, e, f = m1
    A, B, C, D, E, F = m2

    return (
        a*A + c*B,
        b*A + d*B,
        a*C + c*D,
        b*C + d*D,
        a*E + c*F + e,
        b*E + d*F + f,
    )


def transform_point(matrix, x, y):
    a, b, c, d, e, f = matrix
    return a*x + c*y + e, b*x + d*y + f

def get_label(element):
    return (
        element.get(f"{{{INK_NS}}}label")
        or element.get("id")
        or local_name(element)
    )

def walk(element, parent_matrix, current_group, is_root=False):
    """Recursively collect markers while preserving folder hierarchy."""
    own_matrix = multiply(
        parent_matrix,
        parse_transform(element.get("transform", "")),
    )

    tag = local_name(element)

    if tag in ("g", "svg", "a"):
        group = current_group

        if tag == "g" and not is_root:
            label = get_label(element)

            group = current_group.setdefault(
                label,
                {"nodes": []},
            )

        for child in element:
            walk(child, own_matrix, group)

        return

    if tag in ("circle", "ellipse"):
        x = float(element.get("cx", 0))
        y = float(element.get("cy", 0))

    elif tag == "rect":
        x = float(element.get("x", 0)) + (
            float(element.get("width", 0)) / 2
        )
        y = float(element.get("y", 0)) + (
            float(element.get("height", 0)) / 2
        )

    elif tag == "use":
        x = float(element.get("x", 0))
        y = float(element.get("y", 0))

    else:
        return

    px, py = transform_point(own_matrix, x, y)

    current_group["nodes"].append({
        "label": get_label(element),
        "x": round(px, 4),
        "y": round(py, 4),
    })

def main():
    folder = Path(__file__).resolve().parent
    output_folder = folder / "Marker_Coords"
    output_folder.mkdir(exist_ok=True)

    svg_files = sorted(
        path for path in folder.glob("*.svg")
        if path.is_file()
    )

    if not svg_files:
        print(f"No SVG files found in {folder}")
        return

    total_markers = 0
    successful_files = 0
    failed_files = []

    for input_file in svg_files:
        output_file = output_folder / input_file.with_suffix(".json").name

        try:
            tree = etree.parse(str(input_file))
            root = tree.getroot()

            layers = root.xpath(
                ".//*[@inkscape:groupmode='layer']",
                namespaces={"inkscape": INK_NS},
            )

            marker_layers = [
                layer for layer in layers
                if layer.get(f"{{{INK_NS}}}label") == "Markers"
            ]

            if len(marker_layers) != 1:
                available = [
                    layer.get(f"{{{INK_NS}}}label")
                    for layer in layers
                ]

                raise RuntimeError(
                    "Expected exactly one layer named 'Markers'. "
                    f"Found {len(marker_layers)}. "
                    f"Available layers: {available}"
                )

            marker_layer = marker_layers[0]

            ancestors = list(marker_layer.iterancestors())
            matrix = (1, 0, 0, 1, 0, 0)

            for ancestor in reversed(ancestors):
                matrix = multiply(
                    matrix,
                    parse_transform(
                        ancestor.get("transform", "")
                    ),
                )

            data = {}
            walk(marker_layer, matrix, data, is_root=True)

            with output_file.open(
                "w", encoding="utf-8"
            ) as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")

            def count_markers(group):
                count = len(group.get("nodes", []))

                for key, value in group.items():
                    if key != "nodes" and isinstance(value, dict):
                        count += count_markers(value)

                return count

            marker_count = count_markers(data)
            total_markers += marker_count
            successful_files += 1

            print(
                f"{input_file.name}: exported {marker_count} markers "
                f"to {output_file.name}"
            )

        except Exception as error:
            failed_files.append(input_file.name)
            print(f"ERROR processing {input_file.name}: {error}")

    print(
        f"\nFinished. Exported {total_markers} markers "
        f"from {successful_files} SVG files."
    )

    if failed_files:
        print("Files with errors: " + ", ".join(failed_files))

if __name__ == "__main__":
    main()