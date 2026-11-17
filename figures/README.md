# 综述插图与表格

2026-10-26：按已确认方案重绘三张综述图并插入正文。以问题介绍、算法分类和跨偏好组织方式为主，不包含数值反例或性能排名。四张既有表格保留。

| 图 | 文件名 | 位置 | 当前正文页 |
|---|---|---|---|
| 1 | problem_overview | 第2.2节末：给定偏好下的决策问题 | 3 |
| 2 | solver_taxonomy | 第5章导读后、第5.1节前：代表性求解机制 | 16 |
| 3 | preference_reuse | 第5.4节导读后：三种跨偏好组织方式 | 23 |

表1–4对应准则组成、求解路线、离线评价信息和应用证据，当前分别位于第10、30、35、37页。主稿共49页。

## 文件

每图提供嵌入字体 PDF、可编辑 SVG、600 dpi PNG 和 LZW 压缩 TIFF。图宽均为160 mm，正文按自然尺寸插入，不缩放。

- `figure_bundle.pdf`：三张独立矢量图。
- `overview.png`：三图浏览总览。
- `../audit/survey_figure_preview_2026-10-26.pdf`：三张图在论文中的整页预览，包含图注。
- `figure_assets.zip`：三图、四表、源码、图注、结构数据及检查记录；不是完整 LaTeX 工程。
- `source_data.json`：图的节点、路径、分类和文献键；无实验数据。
- `captions.tex`：从主稿同步导出的三条图注。

旧图已从活动素材目录移出，完整保存在 `../audit/figure_table_before_survey_figures_2026-10-26.zip`。

## 字体与复现

中文使用 FandolSong，西文使用 Latin Modern Roman，数学使用 Computer Modern。普通文字五号10.5 PDF pt，数学上下标7.35 PDF pt；正文约11.955 PDF pt。SVG 保留 text/tspan 和组件分组，编辑时须安装相应字体。PDF 已嵌入字体；不分发字体文件。

使用具备 requirements-figures.txt 所列依赖的 Python 环境运行 `python render_figures.py`；`--only F1`、`F2`、`F3` 可单独重绘。需要 nature-figure 审计脚本，使用 `--audit-scripts` 指定其目录。`MOO_TEX_FONTS` 可指向包含 fandol/ 和 lm/ 的 TeX 字体目录。

字体导出保留既有 CFF 到 glyf 的转换与嵌入校验，防止中文在 PDF 中不可见。运行时转换缓存不属于提交素材。

## 设计与核查

采用白底、低饱和分组、短标签与对齐路径。分类关系不用流程箭头，方法族不表示互斥或穷尽；GPI 与整条策略选择分开，目标回报与偏好输入分开。参考学术论文的简洁标注和留白，图形均独立绘制，没有复制第三方图稿。

检查记录见 `../audit/survey_figure_implementation_2026-10-26.md` 与对应 QA 目录。PDF 字号、碰撞及多面板对齐检查通过。通用源码检查预设无衬线字体，本文遵循用户要求采用正文宋体，记录为样式例外；160 mm 宽度同样按当前主稿设置，不套用 Nature 的89/183 mm默认尺寸。
