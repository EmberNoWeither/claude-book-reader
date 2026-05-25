# 性能基线（Phase 5 R1）

## 状态

性能压测尚未执行。当前 R1 完成：测试基础设施 + 异常处理 + 日志，性能优化推迟到 R3。

## 基线数据采集计划

待获取一份 500+ 页的真实 PDF（如《Deep Learning》或《Pattern Recognition and Machine Learning》）后执行：

```bash
# 用 cProfile 抓三个场景
python -m cProfile -o open.prof main.py  # 然后手动开书
python -m cProfile -o scroll.prof main.py  # 连续滚动 100 页
python -m cProfile -o jump.prof main.py  # 跨章节跳转

# 用 snakeviz 查看
pip install snakeviz
snakeviz open.prof
```

## 指标目标

| 指标 | 目标 | 当前 | 备注 |
|---|---|---|---|
| 500 页 PDF 打开时间 | < 2s | — | 不含全文索引建设 |
| 连续滚动 FPS | ≥ 30fps | — | 含虚拟渲染 |
| 跨章节跳转响应 | < 100ms | — | LRU 命中率影响 |
| 内存峰值（500 页） | < 800MB | — | 含 PageRenderer 40 页缓存 |

## 已知潜在瓶颈（待数据验证）

1. **`PdfEngine.get_page_words()` 重复调用**
   - 文字选中 / 双击选词 / 高亮恢复都会重新解析页面 words
   - 优化方向：在 `PdfEngine` 加 LRU 缓存（key=page_num）

2. **`_redraw_note_highlights()` 全量重绘**
   - 每次滚动可见页变化都重新创建所有高亮 QGraphicsRectItem
   - 优化方向：增量更新，只处理新可见/失活的页

3. **大批量 Whoosh 索引**
   - `index_book_pages()` 一次性写入大文档可能 OOM
   - 当前未实现"导入时建索引"流程，待 Phase 5 R2/R3 评估

## 优化原则

- 测出再优化，不预先优化
- 每项优化前后都要重新跑基线
- 用 `tracemalloc` 验证内存修复
