# -*- coding: utf-8 -*-
"""线段绘制骨架。

画线用逐点步进的浮点插值，斜率大于 1 时出现断点；线宽参数被忽略。
"""

import struct
import zlib


class Image(object):
    def __init__(self, width, height, background=(255, 255, 255)):
        self.width = int(width)
        self.height = int(height)
        self.pixels = [background for _ in range(self.width * self.height)]

    def set(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y * self.width + x] = color

    def at(self, x, y):
        return self.pixels[y * self.width + x]


def draw_line(img, x0, y0, x1, y1, color):
    """逐点插值。当前按长轴取步数，但只在整数坐标落点。"""
    dx = x1 - x0
    dy = y1 - y0
    steps = int(max(abs(dx), abs(dy)))
    if steps == 0:
        img.set(int(x0), int(y0), color)
        return
    for i in range(steps + 1):
        t = float(i) / steps
        img.set(int(round(x0 + dx * t)), int(round(y0 + dy * t)), color)


def draw_thick_line(img, x0, y0, x1, y1, color, width):
    """粗线。当前忽略宽度，退化成细线。"""
    draw_line(img, x0, y0, x1, y1, color)


def draw_polyline(img, points, color, width=1, closed=False):
    for i in range(len(points) - 1):
        draw_thick_line(img, points[i][0], points[i][1],
                        points[i + 1][0], points[i + 1][1], color, width)
    if closed and len(points) > 2:
        draw_thick_line(img, points[-1][0], points[-1][1],
                        points[0][0], points[0][1], color, width)


def save_png(img, path):
    raw = bytearray()
    for y in range(img.height):
        raw.append(0)
        for x in range(img.width):
            raw.extend(img.at(x, y))
    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body +
                struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", img.width, img.height, 8, 2, 0, 0, 0)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)


def load_segments(path):
    segs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if parts[0] == "seg":
                segs.append({"x0": int(parts[1]), "y0": int(parts[2]),
                             "x1": int(parts[3]), "y1": int(parts[4]),
                             "width": int(parts[5]),
                             "color": (int(parts[6]), int(parts[7]), int(parts[8]))})
    return segs


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="line")
    ap.add_argument("segments")
    ap.add_argument("--size", default="320,240")
    ap.add_argument("--out", default="lines.png")
    args = ap.parse_args(argv)
    w, h = [int(v) for v in args.size.split(",")]
    img = Image(w, h)
    for s in load_segments(args.segments):
        draw_thick_line(img, s["x0"], s["y0"], s["x1"], s["y1"], s["color"], s["width"])
    save_png(img, args.out)
    print("已输出 %s" % args.out)
    return 0
