"""
This is the implementation of the OGN node defined in Ogn3dText.ogn
"""

import omni.graph.core as og
import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom


def parse_proto_name(name: str) -> str:
    """Parses a letter Prim name according to the rules to extract the represented character
    Args:
        name The Prim name to parse

    Returns:
        empty string if name is not valid, otherwise the represented character
    """
    c = ""
    if name.startswith("alpha_"):
        c = name[-1]
    elif name.startswith("chr_"):
        try:
            c = chr(int(name[4:]))
        except ValueError:
            pass
    return c


class OgnGenerate3dText:
    @staticmethod
    def compute(db) -> bool:
        stage = omni.usd.get_context().get_stage()

        if not db.inputs.fontPrim:
            db.log_error("inputs:fontPrim must be specified")
            return False

        if not db.inputs.instancerPrim:
            # Avoid warning
            db.log_error("inputs:instancerPrim must be specified")
            return False

        font_prim = stage.GetPrimAtPath(str(db.inputs.fontPrim[0]))
        if not font_prim:
            db.log_error(f"inputs:fontPrim {db.inputs.fontPrim[0]} not found")
            return False

        # Update the font mapping
        letter_meshes = font_prim.GetFilteredChildren(Usd.PrimAllPrimsPredicate)
        font_letters_mapping = {}
        font_letters = []
        letter_index = 0
        for letter_mesh in letter_meshes:
            path = letter_mesh.GetPath()
            name = path.name
            chr = parse_proto_name(name)
            if chr:
                font_letters.append(path)
                font_letters_mapping[chr] = letter_index
                letter_index += 1
        font_letters_mapping[" "] = None

        # Parse the text, all unsupported characters are replaced by spaces
        parsed_text = db.inputs.text
        unparsed = set([c for c in db.inputs.text if c not in font_letters_mapping])
        if unparsed:
            parsed_text = "".join([" " if c in unparsed else c for c in db.inputs.text])
            db.log_warning(
                f"The characters {', '.join(unparsed)} have no corresponding letter mesh under {font_prim.GetPath()}"
            )

        instancer_prim = stage.GetPrimAtPath(str(db.inputs.instancerPrim[0]))
        if not instancer_prim:
            db.log_error(f"inputs:instancerPrim {db.inputs.instancerPrim[0]} not found")
            return False

        # Get the instancer as PointInstancer
        instancer = UsdGeom.PointInstancer(instancer_prim)
        if not instancer:
            db.log_error(f"inputs:instancerPrim {db.inputs.instancerPrim[0]} is not a valid PointInstancer")
            return False

        attr = instancer.CreatePrototypesRel()
        targets = attr.GetTargets()

        # Support real-time change on the fontPrim children by user
        # We need to make sure the targets list and font_letters list have the exact same prims in the same order
        rebuild_targets = len(targets) != len(font_letters)
        if not rebuild_targets:
            for target, letter_path in zip(targets, font_letters):
                if target.pathString != letter_path:
                    # Clean up relationships
                    rebuild_targets = True
                    break
        if rebuild_targets:
            # Add relationships to the instancer. The order corresponds to the prototype indices
            attr.ClearTargets(removeSpec=True)
            for letter_path in font_letters:
                attr.AddTarget(letter_path)

        # Alignment
        start_position = 0
        spacing = db.inputs.characterSpacing * db.inputs.scale
        if db.inputs.alignment == db.tokens.Center:
            start_position = -(spacing * (len(parsed_text) - 1)) / 2
        elif db.inputs.alignment == db.tokens.Right:
            start_position = -(spacing * (len(parsed_text) - 1))

        # Scale
        letter_scale = Gf.Vec3f(db.inputs.scale)

        # Space management, simply treat spaces as an empty character
        non_space_letters = [(i, c) for i, c in enumerate(parsed_text) if not c.isspace()]
        with Sdf.ChangeBlock():
            instancer.CreatePositionsAttr([(start_position + spacing * i, 0, 0) for i, _ in non_space_letters])
            instancer.CreateProtoIndicesAttr([font_letters_mapping[letter] for _, letter in non_space_letters])
            instancer.CreateScalesAttr([letter_scale] * len(non_space_letters))

        db.outputs.execOut = og.ExecutionAttributeState.ENABLED
        return True
