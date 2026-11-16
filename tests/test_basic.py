# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from line.core import (  # noqa: E402
    Image, draw_line, draw_thick_line, draw_polyline, load_segments, SS,
)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def _non_white(img):
    """所有非背景像素的坐标集合。"""
    out = set()
    for y in range(img.height):
        for x in range(img.width):
            if img.at(x, y) != WHITE:
                out.add((x, y))
    return out


def _is_4_connected(points):
    """点集是否构成一个 4-连通整体（无断点、无孤岛）。"""
    if not points:
        return False
    seen = {next(iter(points))}
    stack = list(seen)
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) in points and (nx, ny) not in seen:
                seen.add((nx, ny))
                stack.append((nx, ny))
    return seen == points


# ---------------------------------------------------------------- 基础骨架测试

def test_image_bounds():
    img = Image(10, 10)
    img.set(-1, 0, (0, 0, 0))
    assert img.at(0, 0) == WHITE


def test_draw_horizontal():
    img = Image(10, 4)
    draw_line(img, 1, 2, 8, 2, (0, 0, 0))
    assert img.at(1, 2) == (0, 0, 0)
    assert img.at(8, 2) == (0, 0, 0)


def test_load_segments():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "data", "segments.txt")
    if not os.path.exists(path):
        return
    segs = load_segments(path)
    assert len(segs) == 6
    assert segs[0]["width"] == 1


# ---------------------------------------------------------------- 斜率覆盖 / 连通性

SLOPES = [
    ("horizontal", (10, 20), (90, 20)),
    ("vertical", (50, 10), (50, 90)),
    ("diagonal45", (10, 10), (80, 80)),
    ("near-vertical", (50, 10), (53, 90)),   # dy/dx ≈ 26.7
    ("shallow", (10, 30), (90, 40)),         # dy/dx = 0.125
    ("negative", (10, 90), (90, 20)),
]


def test_slopes_connected_no_gaps():
    """水平、垂直、45 度、接近竖直等斜率都必须连成一条 4-连通线。"""
    for name, p0, p1 in SLOPES:
        img = Image(110, 110)
        draw_line(img, p0[0], p0[1], p1[0], p1[1], BLACK)
        points = _non_white(img)
        assert points, name
        assert _is_4_connected(points), name
        # 两个端点所在像素必须被覆盖（含覆盖即算）。
        assert p0 in points, name
        assert p1 in points, name


def test_thick_lines_connected():
    """各宽度粗线同样连成一片，且包含两端点像素。"""
    for width in (1, 2, 3, 5, 7, 9):
        img = Image(110, 110)
        draw_thick_line(img, 12, 15, 95, 88, BLACK, width)
        points = _non_white(img)
        assert _is_4_connected(points), width
        assert (12, 15) in points and (95, 88) in points, width


def test_no_staircase_gaps_in_thick_line():
    """宽线内部不允许出现背景孔洞（阶梯状缺口）。"""
    img = Image(120, 120)
    draw_thick_line(img, 15, 20, 105, 100, BLACK, 7)
    points = _non_white(img)
    # 任意被覆盖像素的 4 邻域里，背景像素只能出现在整体外围：
    # 等价判据 —— 背景像素不能被覆盖像素四面包围。
    covered = points
    for x, y in covered:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in covered:
                # 该背景像素必须能走到画布边缘，否则就是内部孔洞。
                assert _reaches_border(img, covered, nx, ny), (x, y, nx, ny)


def _reaches_border(img, covered, sx, sy):
    seen = {(sx, sy)}
    stack = [(sx, sy)]
    while stack:
        x, y = stack.pop()
        if x == 0 or y == 0 or x == img.width - 1 or y == img.height - 1:
            return True
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < img.width and 0 <= ny < img.height \
                    and (nx, ny) not in covered and (nx, ny) not in seen:
                seen.add((nx, ny))
                stack.append((nx, ny))
    return False


# ---------------------------------------------------------------- 对称性

def test_reversed_endpoints_same_pixel_set():
    """端点对调后，落点集合必须完全一致（集合比较，不比较顺序）。"""
    for name, p0, p1 in SLOPES:
        forward = Image(110, 110)
        reverse = Image(110, 110)
        draw_line(forward, p0[0], p0[1], p1[0], p1[1], BLACK)
        draw_line(reverse, p1[0], p1[1], p0[0], p0[1], BLACK)
        assert _non_white(forward) == _non_white(reverse), name


def test_reversed_thick_line_same_pixels_and_grays():
    """粗线对调端点后，连每个像素的灰度（覆盖率）都完全一致。"""
    for width in (1, 2, 5, 9):
        p0, p1 = (13, 17), (97, 83)
        forward = Image(120, 120)
        reverse = Image(120, 120)
        draw_thick_line(forward, p0[0], p0[1], p1[0], p1[1], BLACK, width)
        draw_thick_line(reverse, p1[0], p1[1], p0[0], p0[1], BLACK, width)
        fmap = {(x, y): forward.at(x, y)
                for y in range(120) for x in range(120)
                if forward.at(x, y) != WHITE}
        rmap = {(x, y): reverse.at(x, y)
                for y in range(120) for x in range(120)
                if reverse.at(x, y) != WHITE}
        assert set(fmap) == set(rmap), width
        assert fmap == rmap, width


# ---------------------------------------------------------------- 宽度生效

def test_widths_cover_different_counts():
    """宽度 1..9 全部生效，覆盖像素数严格递增，2 与 5 明显不同。"""
    counts = {}
    for width in range(1, 10):
        img = Image(140, 140)
        draw_thick_line(img, 20, 30, 120, 110, BLACK, width)
        counts[width] = len(_non_white(img))
    for width in range(2, 10):
        assert counts[width] > counts[width - 1], (width, counts)
    assert counts[5] > counts[2] * 1.5, (counts[2], counts[5])


def test_width_nine_actual_thickness():
    """宽度 9 的竖线，中段实际覆盖 9 列像素。"""
    img = Image(40, 120)
    draw_thick_line(img, 20, 10, 20, 100, BLACK, 9)
    mid_row = 55
    cols = [x for x in range(40) if img.at(x, mid_row) != WHITE]
    assert len(cols) == 9, cols
    assert cols == list(range(16, 25)), cols


def test_width_two_vs_five_horizontal():
    """同一水平线段，宽度 2 与 5 覆盖行数明显不同。"""
    def rows_for(width):
        img = Image(120, 40)
        draw_thick_line(img, 10, 20, 110, 20, BLACK, width)
        return {y for x in range(120) for y in range(40)
                if img.at(x, y) != WHITE}
    assert len(rows_for(2)) == 3
    assert len(rows_for(5)) == 5


# ---------------------------------------------------------------- 端点形状

def test_round_caps_extend_beyond_endpoint():
    """粗线端点是圆头：端外行有覆盖且逐行收窄，硬切口不会这样。"""
    img = Image(60, 120)
    draw_thick_line(img, 30, 40, 30, 80, BLACK, 7)
    # 中段应覆盖满宽 7 列。
    mid_cols = {x for x in range(60) if img.at(x, 60) != WHITE}
    assert len(mid_cols) == 7
    # 圆头越过端点 7 个像素：最外端只剩 3 列（圆头尖端收窄）。
    cap_cols = {x for x in range(60) if img.at(x, 33) != WHITE}
    assert cap_cols == {29, 30, 31}
    assert len(cap_cols) < len(mid_cols), "圆头末端应明显收窄"
    # 再往外没有任何覆盖（圆头在此终止，不是无限延伸的硬切口）。
    assert all(img.at(x, 32) == WHITE for x in range(60))
    # 端点所在行仍是全宽（中心线延长保证端点像素被完整涂满）。
    assert {x for x in range(60) if img.at(x, 40) != WHITE} == mid_cols


def test_round_caps_symmetric_about_endpoint():
    """两个圆头轮廓一致：两端外侧等距行的覆盖列集合相同。"""
    img = Image(60, 120)
    draw_thick_line(img, 30, 40, 30, 80, BLACK, 7)
    for d in (1, 3, 5, 7):
        top = {x for x in range(60) if img.at(x, 40 - d) != WHITE}
        bottom = {x for x in range(60) if img.at(x, 80 + d) != WHITE}
        assert top == bottom, d
    # 圆头之外完全空白。
    assert all(img.at(x, 32) == WHITE for x in range(60))
    assert all(img.at(x, 88) == WHITE for x in range(60))


# ---------------------------------------------------------------- 折线连接

def test_polyline_joint_not_broken():
    """折线直角连接处不能出现断裂：顶点邻域全部被覆盖。"""
    img = Image(120, 120)
    draw_polyline(img, [(20, 30), (80, 30), (80, 90)], BLACK, width=5)
    points = _non_white(img)
    assert _is_4_connected(points)
    # 顶点 (80,30) 的 3x3 邻域全部被覆盖（两段圆头在此重叠）。
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            assert (80 + dx, 30 + dy) in points, (dx, dy)


def test_closed_polyline_is_one_connected_shape():
    img = Image(120, 120)
    draw_polyline(img, [(25, 25), (95, 25), (95, 95), (25, 95)],
                  BLACK, width=4, closed=True)
    points = _non_white(img)
    assert _is_4_connected(points)


# ---------------------------------------------------------------- 抗锯齿

def test_antialiased_edge_gray_levels():
    """斜边边缘存在多级灰度，且灰度只能是覆盖率 k/16 对应的混合值。"""
    img = Image(120, 120)
    draw_line(img, 10, 100, 110, 20, BLACK)
    grays = {img.at(x, y)[0]
             for y in range(120) for x in range(120)
             if img.at(x, y) != WHITE}
    # 不止纯黑一级，说明有灰度过渡。
    assert len(grays) >= 3, grays
    # 黑在白底上按覆盖率混合：值必须等于 round(255*(1-k/16))。
    allowed = {int(round(255 * (1.0 - k / (SS * SS))))
               for k in range(1, SS * SS + 1)}
    assert grays <= allowed, grays - allowed


def test_edge_coverage_matches_gray():
    """边缘像素灰度与其覆盖率一致（黑底白景反算覆盖率，误差不超过 1 级）。"""
    img = Image(120, 120)
    draw_line(img, 10, 100, 110, 20, BLACK)
    edge_found = False
    for y in range(120):
        for x in range(120):
            v = img.at(x, y)[0]
            if 0 < v < 255:
                edge_found = True
                coverage = (255 - v) / 255.0
                # 覆盖率必须落在 1/16 的量化网格上（允许四舍五入误差）。
                k = round(coverage * SS * SS)
                assert 1 <= k <= SS * SS - 1
                assert abs(coverage - k / (SS * SS)) < 1.0 / 255.0 + 1e-9
    assert edge_found


def test_horizontal_axis_aligned_line_is_crisp():
    """轴对齐线的中心线完全不发虚（覆盖率 100%，纯目标色）。"""
    img = Image(100, 40)
    draw_thick_line(img, 10, 20, 90, 20, BLACK, 5)
    for x in range(10, 91):
        assert img.at(x, 20) == BLACK
