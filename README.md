# 给定偏好下的多目标序贯决策体系研究现状及探讨

文献综述 LaTeX 工程。入口为 `main.tex`，正文共八章，参考文献采用 GB/T 7714—2015 顺序编码制。

## 编译

安装包含中文支持的 TeX Live（或 MacTeX），在仓库根目录运行：

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
latexmk -c main.tex
```

也可将工程上传至 Overleaf，选择 XeLaTeX 编译器，以 `main.tex` 为主文件。

## 文件

- `main.tex`、`chapter1.tex` 至 `chapter8.tex`：入口与正文。
- `references.bib`、`references_added.tex`：书目数据与参考文献表。
- `gbt7714-2015-numeric.bst`：参考文献样式，保留文件中的 LPPL 许可说明。
- `figures/`：插图、源文件与绘图脚本；依赖见 `requirements-figures.txt`。
- `tables/`：表格源码。
- `main.pdf`：随源码附带的编译结果。

本次上传来自本地 `Literture_Review/latex/`，未包含 `audit/` 核查材料、历史压缩包、工具记忆与编译中间文件。正文、书目和图表源文件保持原样。
