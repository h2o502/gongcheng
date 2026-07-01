#!/usr/bin/env python3
"""
CodeBlockRenderer: 代码块段落，带浅灰背景 + 四边框 + Consolas 等宽字体。
直接操作 Word XML，不依赖 Building Blocks。
"""

from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


CODE_BG_COLOR   = 'F0F0F0'   # 浅灰背景
BORDER_COLOR    = 'CCCCCC'   # 边框色（浅灰）
BORDER_SIZE     = '4'         # 边框粗细（0.5pt）
BORDER_SPACE    = '4'         # 边框与文字间距（twips）
CODE_FONT       = 'Consolas'
CODE_FONT_SIZE  = 10          # pt


def _set_run_font(run, font_name, font_size):
    """设置 run 的字体和字号，中英文字体统一"""
    run.font.name = font_name
    run.font.size = Pt(font_size)
    try:
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    except Exception:
        pass


def _apply_paragraph_shading(p, fill_color):
    """给段落加背景色（w:shd）"""
    pPr = p._p.get_or_add_pPr()
    # 移除旧的 shd
    for old in pPr.findall(qn('w:shd')):
        pPr.remove(old)
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  fill_color)
    pPr.append(shd)


def _apply_paragraph_borders(p, color, sz='4', space='4'):
    """给段落加四边框（w:pBdr），形成代码块围边效果"""
    pPr = p._p.get_or_add_pPr()
    # 移除旧的 pBdr
    for old in pPr.findall(qn('w:pBdr')):
        pPr.remove(old)

    pBdr = OxmlElement('w:pBdr')
    for side in ('top', 'left', 'bottom', 'right'):
        border = OxmlElement(f'w:{side}')
        border.set(qn('w:val'),   'single')
        border.set(qn('w:sz'),    sz)
        border.set(qn('w:space'), space)
        border.set(qn('w:color'), color)
        pBdr.append(border)
    pPr.append(pBdr)


def _apply_spacing(p, before='60', after='60', line='240'):
    """设置段落间距（收紧行距，模拟代码块紧凑感）"""
    pPr = p._p.get_or_add_pPr()
    for old in pPr.findall(qn('w:spacing')):
        pPr.remove(old)
    spacing = OxmlElement('w:spacing')
    spacing.set(qn('w:before'),   before)   # 3pt 段前
    spacing.set(qn('w:after'),    after)    # 3pt 段后
    spacing.set(qn('w:line'),     line)     # 固定行距
    spacing.set(qn('w:lineRule'), 'auto')
    pPr.append(spacing)


def add_code_block_to_doc(doc, code_text, language=None):
    """
    插入代码块到 Word：每行一个段落，灰色背景 + 四边框 + Consolas。
    视觉上等同于 Word 原生代码块效果。
    """
    lines = code_text.split('\n')

    for line in lines:
        p = doc.add_paragraph()

        # 1. 浅灰背景
        _apply_paragraph_shading(p, CODE_BG_COLOR)

        # 2. 四边框（浅灰细线）
        _apply_paragraph_borders(p, BORDER_COLOR, BORDER_SIZE, BORDER_SPACE)

        # 3. 紧凑行间距
        _apply_spacing(p)

        # 4. 文本
        if line:
            run = p.add_run(line)
            _set_run_font(run, CODE_FONT, CODE_FONT_SIZE)
