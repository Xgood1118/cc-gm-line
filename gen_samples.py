# -*- coding: utf-8 -*-
"""生成一组线段：陡斜率、缓斜率、水平、垂直、对角，宽度从 1 到 9。"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

SEGS = """# x0 y0 x1 y1 width r g b
seg 20 20 200 40 1 200 60 60
seg 20 60 40 200 3 60 140 200
seg 20 210 300 210 5 60 200 100
seg 300 20 300 200 9 220 180 60
seg 40 120 280 160 7 140 80 200
seg 100 30 130 190 2 30 30 30
"""

if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    path = os.path.join(HERE, "data", "segments.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(SEGS)
    print("已生成", path)
