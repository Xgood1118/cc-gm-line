# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from line.core import Image, draw_line, load_segments  # noqa: E402


def test_image_bounds():
    img = Image(10, 10)
    img.set(-1, 0, (0, 0, 0))
    assert img.at(0, 0) == (255, 255, 255)


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
