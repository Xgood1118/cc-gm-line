# 线段绘制

骨架能把线段画到图上，但陡斜率的线和宽线都不对。

## 已知缺口

- `draw_line` 用浮点插值再四舍五入，斜率大于 1 时同一行会连续落多个点、相邻行缺一整段，
  竖直方向的线是断的。
- 端点处理不统一，反着画同一条线（起点终点对调）结果不同。
- `draw_thick_line` 忽略 `width`，宽度参数完全无效。
- 没有端点形状，粗线两端是直角切口。
- 没有抗锯齿，斜线边缘是硬锯齿。

## 运行

```
python gen_samples.py
python -m line.cli data/segments.txt --size 320,240 --out lines.png
python -m pytest tests -q
```

`segments.txt` 六条线：缓斜率、陡斜率、水平、垂直、对角、宽度从 1 到 9。
