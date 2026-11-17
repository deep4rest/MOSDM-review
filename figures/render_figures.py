#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.9", "numpy>=2.0", "pymupdf>=1.24", "fonttools>=4.59"]
# ///
"""Render three survey schematics: problem, solver taxonomy, preference reuse.

Run with Python and the nature-figure audit scripts available on PYTHONPATH,
or pass --audit-scripts. No empirical observations, invented performance values, or random samples are used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
from fractions import Fraction
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
from matplotlib.path import Path as MplPath
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

OUT = Path(__file__).resolve().parent
QA = OUT.parent / "audit" / "survey_figure_qa_2026-10-26"
WIDTH_MM = 160.0
WIDTH_PT = WIDTH_MM / 25.4 * 72
INK = "#202020"
BLUE = "#356B8C"
BLUE_FILL = "#EAF1F5"
WARM = "#A56D43"
WARM_FILL = "#F7EEE5"
GREY = "#73808A"
PALE = "#F3F5F6"
LINE = "#B6C0C8"
# ctex's \zihao{5} uses 10.5 bp, measured as 10.5 points in the final PDF.
FONT = 10.5
FONT_CJK = None
FONT_LATIN = None
TEXT_RECORDS: list[tuple] = []


def embedding_font(source):
    """Keep the manuscript face while supplying true glyf data to PDF Type 2.

    Matplotlib's Type 42 exporter otherwise wraps a CFF OpenType font as a
    FontFile2 stream; some PDF renderers then silently omit its glyphs.
    Convert the outline format only, retaining names, metrics and layout.
    """
    cache = Path(tempfile.gettempdir()) / "moo-manuscript-fonts-v1"
    cache.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    target = cache / f"{source.stem}-{digest}.ttf"
    if target.exists():
        return target
    original = TTFont(source)
    if "glyf" in original:
        return source
    glyph_set = original.getGlyphSet()
    glyphs = {}
    for name in original.getGlyphOrder():
        pen = TTGlyphPen(glyph_set)
        glyph_set[name].draw(Cu2QuPen(pen, max_err=0.3, reverse_direction=True))
        glyphs[name] = pen.glyph()
    builder = FontBuilder(original["head"].unitsPerEm, isTTF=True)
    builder.setupGlyphOrder(original.getGlyphOrder())
    builder.setupCharacterMap(original.getBestCmap())
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(original["hmtx"].metrics)
    builder.setupHorizontalHeader(ascent=original["hhea"].ascent,
                                  descent=original["hhea"].descent,
                                  lineGap=original["hhea"].lineGap)
    builder.font["name"] = original["name"]
    builder.font["OS/2"] = original["OS/2"]
    builder.setupPost()
    for tag in ["BASE", "GDEF", "GPOS", "GSUB", "kern", "vhea", "vmtx"]:
        if tag in original:
            builder.font[tag] = original[tag]
    builder.save(target)
    return target


def configure_font():
    global FONT_CJK, FONT_LATIN
    tex_fonts = Path(os.environ.get("MOO_TEX_FONTS", str(Path.home() / "texlive/2026/texmf-dist/fonts/opentype/public")))
    chinese = tex_fonts / "fandol/FandolSong-Regular.otf"
    latin = tex_fonts / "lm/lmroman10-regular.otf"
    logging.getLogger("fontTools").setLevel(logging.ERROR)
    font_manager.fontManager.ttflist = [entry for entry in font_manager.fontManager.ttflist
                                       if entry.name not in {"Latin Modern Roman", "FandolSong"}]
    converted = {}
    for candidate in [chinese, tex_fonts / "fandol/FandolSong-Bold.otf", latin,
                      tex_fonts / "lm/lmroman10-bold.otf", tex_fonts / "lm/lmroman10-italic.otf"]:
        if not candidate.is_file():
            raise RuntimeError(f"Manuscript font unavailable: {candidate.name}")
        converted[candidate] = embedding_font(candidate)
        font_manager.fontManager.addfont(str(converted[candidate]))
    font_manager.fontManager._findfont_cached.cache_clear()
    # Match XeLaTeX's per-script choice, including digits in mixed CJK labels.
    FONT_CJK = font_manager.FontProperties(family=["Latin Modern Roman", "FandolSong"])
    FONT_LATIN = font_manager.FontProperties(fname=str(converted[latin]))
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Latin Modern Roman", "FandolSong"],
        "font.size": 10.5,
        "mathtext.fontset": "cm",
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "axes.unicode_minus": False,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
        "text.color": INK,
        "hatch.linewidth": 0.45,
    })
    FONT_LATIN.set_math_fontfamily("cm")
    FONT_CJK.set_math_fontfamily("cm")
    return "FandolSong / Latin Modern Roman"


def label(ax, x, y, s, size=FONT, ha="center", weight="normal", gid=None):
    artist = ax.text(x, y, s, fontsize=size, color=INK, ha=ha, va="center",
                     fontweight=weight, clip_on=False, linespacing=1.25,
                     fontproperties=FONT_CJK if re.search(r"[\u3000-\u9fff\uff00-\uffef]", s) else FONT_LATIN)
    artist.set_gid(gid or f"label-{ax.figure.axes.index(ax)}-{len(ax.texts)}")
    TEXT_RECORDS.append((ax.figure, artist))
    return artist


def box(ax, x, y, w, h, *, fill=PALE, edge=LINE, lw=0.7, gid=None, radius=1):
    p = FancyBboxPatch((x, y), w, h,
                      boxstyle=f"round,pad=0,rounding_size={radius}",
                      facecolor=fill, edgecolor=edge, linewidth=lw)
    p.set_gid(gid or f"component-{ax.figure.axes.index(ax)}-{len(ax.patches)}")
    ax.add_patch(p)
    return p


def arrow(ax, start, end, *, color=BLUE, lw=1.0, style="-", path=None, gid=None):
    p = FancyArrowPatch(start, end, path=path, arrowstyle="-|>",
                        mutation_scale=8, linewidth=lw, color=color,
                        linestyle=style, shrinkA=0, shrinkB=0,
                        capstyle="round", joinstyle="round") if path is None else FancyArrowPatch(
                            path=path, arrowstyle="-|>", mutation_scale=8,
                            linewidth=lw, color=color, linestyle=style,
                            capstyle="round", joinstyle="round")
    if gid:
        p.set_gid(gid)
    ax.add_patch(p)
    return p


def segment(ax, x1, y1, x2, y2, color=LINE, lw=0.65):
    ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw, solid_capstyle="butt")


def canvas(height_pt):
    fig = plt.figure(figsize=(WIDTH_PT / 72, height_pt / 72), dpi=600)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, WIDTH_PT), ylim=(height_pt, 0))
    ax.set_axis_off()
    return fig, ax


def panel_units(ax):
    fig = ax.figure
    pos = ax.get_position()
    w = pos.width * fig.get_figwidth() * 72
    h = pos.height * fig.get_figheight() * 72
    ax.set(xlim=(0, w), ylim=(h, 0))
    ax.set_axis_off()
    return w, h


def panel_title(ax, letter, title):
    # Fixed physical offsets keep panel labels aligned even for unequal spans.
    ax.annotate(letter, (0, 1), xycoords="axes fraction", xytext=(0, 8),
                textcoords="offset points", fontsize=FONT, fontweight="bold",
                ha="left", va="baseline", color=INK, fontfamily="Latin Modern Roman")
    ax.annotate(title, (0, 1), xycoords="axes fraction", xytext=(15, 8),
                textcoords="offset points", fontsize=FONT,
                ha="left", va="baseline", color=INK, fontproperties=FONT_CJK)


def verify_text_page(fig):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    page = fig.bbox
    for owner, artist in TEXT_RECORDS:
        if owner is not fig:
            continue
        bb = artist.get_window_extent(renderer)
        if bb.x0 < page.x0 - 0.5 or bb.x1 > page.x1 + 0.5 or bb.y0 < page.y0 - 0.5 or bb.y1 > page.y1 + 0.5:
            raise ValueError(f"Text outside canvas: {artist.get_text()!r}")


def verify_pdf_fonts(path):
    import pymupdf
    with pymupdf.open(path) as document:
        fonts = document[0].get_fonts()
        if not fonts:
            raise ValueError("PDF has no embedded, editable text fonts")
        for item in fonts:
            name, extension, _, data = document.extract_font(item[0])
            if not data:
                raise ValueError(f"PDF font is not embedded: {name}")
            if extension == "ttf" and data[:4] not in {b"\x00\x01\x00\x00", b"true"}:
                raise ValueError(f"Invalid TrueType embedding for {name}")


def save(fig, stem, alignment, *, ids=None):
    from audit_panel_alignment import require_matplotlib_panel_alignment
    fig.canvas.draw()
    verify_text_page(fig)
    require_matplotlib_panel_alignment(
        fig, json_out=QA / f"{stem}.alignment.json",
        overlay_svg=QA / f"{stem}.alignment.svg",
        tolerance_pt=1.5, gutter_tolerance_pt=1.5,
        require_panel_labels=alignment, strict=True,
        **({"panel_ids": ids} if ids else {}),
    )
    # Use the full physical canvas: tight cropping would change the typeset size.
    fig.savefig(OUT / f"{stem}.svg", format="svg")
    svg_path = OUT / f"{stem}.svg"
    svg_text = re.sub(r"<!DOCTYPE[^>]*>\s*", "", svg_path.read_text())
    tree = ET.fromstring(svg_text)
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    # In this pt-matched viewBox, CSS px and unitless SVG font attributes both
    # denote user units. Explicit presentation attributes avoid px/pt ambiguity
    # in geometry auditors while preserving the rendered type size.
    for element in tree.iter():
        style = element.get("style", "")
        match = re.search(r"(?:^|;)\s*font-size:\s*([\d.]+)px\s*(?:;|$)", style)
        if match:
            element.set("font-size", match.group(1))
            remaining = re.sub(r"font-size:\s*[\d.]+px\s*;?", "", style).strip(" ;")
            if remaining:
                element.set("style", remaining)
            else:
                element.attrib.pop("style", None)
    # Keep each box and its labels together as one editable SVG component.
    namespace = "{http://www.w3.org/2000/svg}"
    for ax in fig.axes:
        for patch in reversed(ax.patches):
            if not isinstance(patch, FancyBboxPatch) or not patch.get_gid():
                continue
            elements = {e.get("id"): e for e in tree.iter() if e.get("id")}
            shape = elements.get(patch.get_gid())
            if shape is None:
                continue
            parent = next(e for e in tree.iter() if shape in list(e))
            labels = []
            for artist in ax.texts:
                if (artist.get_gid() in elements
                        and elements[artist.get_gid()] in list(parent)
                        and patch.contains_point(
                            ax.transData.transform(artist.get_position()))):
                    labels.append(artist)
            if not labels:
                continue
            group = ET.Element(namespace + "g", {"id": patch.get_gid()})
            ET.SubElement(group, namespace + "title").text = " / ".join(
                t.get_text() for t in labels)
            shape.set("id", patch.get_gid() + "-shape")
            parent.insert(list(parent).index(shape), group)
            parent.remove(shape)
            group.append(shape)
            for artist in labels:
                element = elements[artist.get_gid()]
                if element in list(parent):
                    parent.remove(element)
                    group.append(element)
    svg_path.write_text(ET.tostring(tree, encoding="unicode"))
    fig.savefig(OUT / f"{stem}.pdf", format="pdf", metadata={"Title": stem, "Creator": "Matplotlib"})
    verify_pdf_fonts(OUT / f"{stem}.pdf")
    fig.savefig(OUT / f"{stem}.png", format="png", dpi=600)
    fig.savefig(OUT / f"{stem}.tiff", format="tiff", dpi=600,
                pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)
    print(f"Rendered {stem}: {WIDTH_MM:g} mm wide")


TEAL = '#43877F'
TEAL_FILL = '#EDF5F2'


def problem_overview():
    """Policy execution above, preference-defined comparison below."""
    fig, ax = canvas(240)
    # The execution loop does not describe training or online data access.
    box(ax, 8, 45, 84, 48, fill=BLUE_FILL, edge=BLUE)
    label(ax, 50, 60, '决策策略')
    label(ax, 50, 79, r'$\pi$')
    box(ax, 149, 45, 84, 48, fill='white', edge=GREY)
    label(ax, 191, 69, '环境')
    arrow(ax, (96, 69), (145, 69))
    label(ax, 120, 53, r'$a_t$')
    # Rounded return loop: environment supplies available history/information.
    path = MplPath([(191,93),(191,111),(191,121),(181,121),
                    (60,121),(50,121),(50,111),(50,97)],
                   [MplPath.MOVETO,MplPath.LINETO,MplPath.CURVE3,MplPath.CURVE3,
                    MplPath.LINETO,MplPath.CURVE3,MplPath.CURVE3,MplPath.LINETO])
    arrow(ax, None, None, color=GREY, lw=.9, path=path)
    label(ax, 108, 138, '可用信息')
    label(ax, 147, 138, r'$h_t$')
    # Parallel reward channels are symbolic components, not measured data bars.
    arrow(ax, (237,69), (258,69), color=GREY, lw=.85)
    for y,c in [(53,BLUE),(69,TEAL),(85,WARM)]:
        box(ax,264,y-5,25,10,fill=c,edge='none',radius=1)
    label(ax, 277, 106, r'$\mathbf{r}_t$')
    label(ax, 277, 30, '多维回报')
    arrow(ax, (294,69), (342,69), color=GREY,lw=.85)
    label(ax, 319, 46, '时间聚合')
    box(ax, 347, 45, 99, 48, fill=TEAL_FILL,edge=TEAL)
    label(ax,396.5,60,'长期结果')
    label(ax,396.5,79,'回报／轨迹特征')
    arrow(ax,(396.5,97),(396.5,180),color=TEAL,lw=1)
    label(ax,318,133,'策略诱导的')
    label(ax,318,151,'结果分布')
    box(ax,8,184,104,48,fill=WARM_FILL,edge=WARM)
    label(ax,60,199,'给定偏好')
    label(ax,60,218,r'$p$')
    arrow(ax,(116,208),(228,208),color=WARM,lw=1)
    label(ax,172,192,'规定比较方式')
    box(ax,233,184,213,48,fill=PALE,edge=GREY)
    label(ax,339.5,199,'长期准则（含随机性处理）')
    label(ax,339.5,218,r'$J_p(\pi)$')
    save(fig,'problem_overview',False)


def branch(ax, x, y, title, detail, colour):
    # Taxonomic edges intentionally have no arrowhead.
    segment(ax,x,y,x+9,y,color=colour,lw=.85)
    ax.add_patch(Circle((x,y),1.5,facecolor=colour,edgecolor='none'))
    label(ax,x+16,y,title,ha='left')
    if detail:
        label(ax,x+16,y+18,detail,ha='left')


def solver_taxonomy():
    """Three information conditions; representative mechanisms within each."""
    height=307
    fig=plt.figure(figsize=(WIDTH_PT/72,height/72),dpi=600)
    # Real equal-area axes allow physical panel alignment to be audited.
    gs=fig.add_gridspec(1,3,left=.018,right=.982,bottom=.20,top=.86,wspace=.10)
    axes=[fig.add_subplot(gs[0,i]) for i in range(3)]
    for ax,letter,title,subtitle,col,fill in zip(
        axes,['a','b','c'],['模型可用','允许交互','固定历史数据'],
        ['规划与控制','策略学习','离线策略改进'],
        [BLUE,TEAL,WARM],[BLUE_FILL,TEAL_FILL,WARM_FILL]):
        w,h=panel_units(ax)
        panel_title(ax,letter,title)
        box(ax,0,0,w,28,fill=fill,edge='none',radius=2)
        label(ax,w/2,14,subtitle)
        segment(ax,9,46,9,183,color=col,lw=.85)
    a,b,c=axes
    for y,title,detail in [
        (48,'递推规划','标量／扩展状态'),
        (91,'模拟搜索','NLU-MCTS · DMCTS'),
        (134,'数学规划与策略合成','占用测度／可达集'),
        (177,'滚动优化','多目标 MPC')]:
        branch(a,9,y,title,detail,BLUE)
    # Blank space is deliberate: it avoids fabricating extra algorithm families.
    for y,title,detail in [(48,'价值学习','标量／向量价值'),
                            (134,'策略优化','策略梯度／直接搜索')]:
        branch(b,9,y,title,detail,TEAL)
    label(b,25,170,'含 actor–critic',ha='left')
    for y,title,detail in [
        (48,'基线保护与候选检验','MO-SPIBB · MO-HCPI'),
        (112,'悲观对偶优化','PEDI'),
        (177,'正则占用优化','FairDICE · AETDICE')]:
        branch(c,9,y,title,detail,WARM)
    # Common bands are annotations, not extra comparison panels.
    fig.text(.5,.971,'给定偏好与长期准则',ha='center',va='top',
             fontsize=FONT,fontproperties=FONT_CJK)
    fig.text(.5,.122,'模型可由机理知识、交互数据或固定数据获得',ha='center',va='center',
             fontsize=FONT,fontproperties=FONT_CJK)
    fig.text(.5,.045,'准则属性与求解机制交叉；图示为代表性方法族',ha='center',va='center',
             fontsize=FONT,fontproperties=FONT_CJK)
    save(fig,'solver_taxonomy',True,ids=['a','b','c'])


def preference_reuse():
    """Matched query-to-policy paths reveal what is shared across preferences."""
    height=333
    fig=plt.figure(figsize=(WIDTH_PT/72,height/72),dpi=600)
    gs=fig.add_gridspec(3,1,left=.02,right=.98,bottom=.025,top=.94,hspace=.39)
    axes=[fig.add_subplot(gs[i]) for i in range(3)]
    for ax,letter,title,col in zip(axes,['a','b','c'],
           ['独立求解','候选集合','条件表示'],[GREY,BLUE,TEAL]):
        w,h=panel_units(ax)
        panel_title(ax,letter,title)
        ax.add_patch(Circle((22,34),16,facecolor='white',edgecolor=col,lw=.8))
        label(ax,22,34,r'$p$')
        box(ax,w-46,18,40,32,fill='white',edge=col,radius=1)
        label(ax,w-26,34,r'$\pi_p$')
        arrow(ax,(42,34),(78,34),color=col,lw=.85)
        arrow(ax,(w-89,34),(w-50,34),color=col,lw=.85)
    a,b,c=axes;w,h=panel_units(a)
    box(a,82,14,w-175,40,fill=PALE,edge=GREY)
    label(a,w/2-5,34,'单偏好求解器')
    label(a,w/2,71,'每个给定偏好分别求解')
    # Two offset sheets indicate a reusable library, rather than NN layers.
    box(b,82,6,105,48,fill='white',edge=LINE)
    box(b,87,11,105,48,fill='white',edge=LINE)
    box(b,92,16,105,42,fill=BLUE_FILL,edge=BLUE)
    label(b,144.5,37,'策略／价值库')
    arrow(b,(201,34),(223,34),color=BLUE,lw=.85)
    box(b,227,14,w-320,40,fill=BLUE_FILL,edge=BLUE)
    label(b,227+(w-320)/2,26,'按准则选择')
    label(b,227+(w-320)/2,44,'或策略改进')
    label(b,w/2,77,'整条选择；GPI 按状态改进（有条件）')
    box(c,82,14,115,40,fill='white',edge=TEAL)
    label(c,139.5,26,'偏好输入')
    label(c,139.5,44,'或目标回报')
    arrow(c,(201,34),(223,34),color=TEAL,lw=.85)
    box(c,227,14,w-320,40,fill=TEAL_FILL,edge=TEAL)
    label(c,227+(w-320)/2,26,'共享条件模型')
    label(c,227+(w-320)/2,44,'价值／策略')
    label(c,w/2,77,'目标回报须按原准则选择')
    save(fig,'preference_reuse',True,ids=['a','b','c'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only',choices=['F1','F2','F3'])
    parser.add_argument('--audit-scripts',type=Path,
        default=Path(os.environ.get('NATURE_FIGURE_SCRIPTS',str(Path.home()/'.codex/skills/nature-figure/scripts'))))
    args=parser.parse_args();sys.path.insert(0,str(args.audit_scripts))
    QA.mkdir(parents=True,exist_ok=True)
    family=configure_font()
    (QA/'render_settings.json').write_text(json.dumps({
        'backend':'Python / Matplotlib','width_mm':WIDTH_MM,'font_family':family,
        'math_font':'Computer Modern','font_size_pdf_pt':FONT,'png_dpi':600,
        'physical_alignment_tolerance_pt':1.5,'type':'survey vector schematics; no measured data',
        'style_exception':'Manuscript serif fonts and 160 mm text width are user requirements.'
    },ensure_ascii=False,indent=2)+'\n')
    for key,fn in {'F1':problem_overview,'F2':solver_taxonomy,'F3':preference_reuse}.items():
        if args.only is None or args.only==key:fn()


if __name__=='__main__':main()
