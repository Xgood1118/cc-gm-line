# -*- coding: utf-8 -*-
"""线段绘制器（纯标准库）。

几何模型
--------
一条宽度为 width 的线段被建模为**胶囊体**：到线段的距离不超过
r = width / 2 的所有点，两端是半圆形端帽（round cap）。

中心线沿轴向两端各延长 r，再扣上半径 r 的半圆帽，因此笔画在端点
之外共伸出一个线宽 width，轴对齐笔画能把两个端点像素完整涂满
（端点像素不会因圆帽削角而发灰）；端帽轮廓仍是圆形而非硬切口。
折线各段的圆头在公共顶点处重叠，连接处不会断裂。

抗锯齿
------
对每个像素做 SS x SS 的网格超采样（默认 4x4 = 16 个采样点），
像素覆盖率 = 落在胶囊体内的采样点数 / 采样总数，共 17 级灰度。
最终颜色按覆盖率与画布已有颜色做 source-over 混合，因此边缘像素
的灰度严格等于其覆盖率，同色线段重叠也不会产生接缝。

坐标约定
--------
像素 (x, y) 的中心位于整数坐标 (x, y)，像素方块为
[x-0.5, x+0.5) x [y-0.5, y+0.5)。

胶囊体关于两个端点对称，所以起点终点对调后逐像素覆盖率完全一致。
"""

import math
import struct
import zlib

# 每轴超采样次数；覆盖率分级数 = SS * SS + 1
SS = 4


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


# 像素方块内的采样点偏移（相对像素中心），SS x SS 均匀网格。
_SAMPLE_OFFSETS = tuple(
    ((i + 0.5) / SS - 0.5, (j + 0.5) / SS - 0.5)
    for i in range(SS)
    for j in range(SS)
)


def _composite(img, x, y, coverage, color):
    """按 coverage 把 color 以 source-over 方式混合到像素上。"""
    if coverage <= 0.0:
        return
    idx = y * img.width + x
    if coverage >= 1.0:
        img.pixels[idx] = color
        return
    dst = img.pixels[idx]
    img.pixels[idx] = tuple(
        int(ch * coverage + bg * (1.0 - coverage) + 0.5)
        for ch, bg in zip(color, dst)
    )


def _draw_capsule(img, x0, y0, x1, y1, color, width):
    """绘制带圆形端帽的抗锯齿线段。"""
    r = max(float(width), 1.0) * 0.5
    r2 = r * r
    dx = x1 - x0
    dy = y1 - y0
    length = math.hypot(dx, dy)
    # 浮点反向计算时末位误差的容差，保证端点对调结果逐像素一致。
    eps = 1e-9
    if length == 0.0:
        # 退化线段（两端点重合）：以该点为圆心画一个圆点。
        ex0 = ey0 = x0
        ex1 = ey1 = y0
        length2 = 0.0
        edx = edy = 0.0
    else:
        # 中心线沿轴向两端各延长 r，再由半圆帽收口。
        ux, uy = dx / length, dy / length
        ex0, ey0 = x0 - ux * r, y0 - uy * r
        ex1, ey1 = x1 + ux * r, y1 + uy * r
        edx, edy = ex1 - ex0, ey1 - ey0
        length2 = edx * edx + edy * edy

    # 胶囊体包围盒向外各扩一圈像素，再裁到画布范围内。
    x_lo = max(0, int(math.floor(min(ex0, ex1) - r)) - 1)
    x_hi = min(img.width - 1, int(math.ceil(max(ex0, ex1) + r)) + 1)
    y_lo = max(0, int(math.floor(min(ey0, ey1) - r)) - 1)
    y_hi = min(img.height - 1, int(math.ceil(max(ey0, ey1) + r)) + 1)

    total = SS * SS
    for py in range(y_lo, y_hi + 1):
        for px in range(x_lo, x_hi + 1):
            hits = 0
            for ox, oy in _SAMPLE_OFFSETS:
                sx = px + ox
                sy = py + oy
                if length2 == 0.0:
                    d2 = (sx - x0) ** 2 + (sy - y0) ** 2
                else:
                    t = ((sx - ex0) * edx + (sy - ey0) * edy) / length2
                    if t < 0.0:
                        t = 0.0
                    elif t > 1.0:
                        t = 1.0
                    closest_x = ex0 + t * edx
                    closest_y = ey0 + t * edy
                    d2 = ((sx - closest_x) ** 2 +
                          (sy - closest_y) ** 2)
                if d2 <= r2 + eps:
                    hits += 1
            if hits:
                _composite(img, px, py, hits / float(total), color)


def draw_line(img, x0, y0, x1, y1, color):
    """1 像素宽抗锯齿线段，等价于宽度 1 的粗线。"""
    _draw_capsule(img, x0, y0, x1, y1, color, 1)


def draw_thick_line(img, x0, y0, x1, y1, color, width):
    """带圆形端帽的抗锯齿粗线，width 取 1..9（任意正数均可）。"""
    _draw_capsule(img, x0, y0, x1, y1, color, width)


def draw_polyline(img, points, color, width=1, closed=False):
    """逐段绘制折线；相邻段的圆头端帽在公共顶点重叠，连接不断裂。"""
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
                             "color": (int(parts[6]), int(parts[7]),
                                       int(parts[8]))})
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
        draw_thick_line(img, s["x0"], s["y0"], s["x1"], s["y1"],
                        s["color"], s["width"])
    save_png(img, args.out)
    print("已输出 %s" % args.out)
    return 0
