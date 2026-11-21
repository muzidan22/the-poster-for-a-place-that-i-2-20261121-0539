"""Write the SOLMARA poster to /output/entry.png.

The poster (entry.png, 1024x1024 PNG) sits beside this file, drawn by
poster.py: a sea arch framed against a molten sunset over open water, with the
invented place's name SOLMARA set across the sky. This entrypoint copies those
bytes, so both graded runs write the same file with no network and no fonts.
"""

import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "entry.png")


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "entry.png")
    shutil.copyfile(SOURCE, target)
    print("wrote %s (%d bytes)" % (target, os.path.getsize(target)))
    return target


if __name__ == "__main__":
    main()
