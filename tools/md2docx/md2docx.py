#!/usr/bin/env python3
"""
Markdown to Word converter tool (支持内嵌HTML、Mermaid图表渲染、个性化定制)

个性化定制：
- 全文微软雅黑
- 正文10.5号
- 表格9号
- 标题动态字号（最末级12.5，每升一级+2）

Usage:
    python md2docx.py <input.md> <output.docx>
"""

import sys
import os
import re
import urllib.request
import urllib.parse
import base64
import tempfile
import shutil
import atexit
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from html.parser import HTMLParser
import mammoth
from bs4 import BeautifulSoup

# 代码块语法高亮（支持 Pygments）
try:
    from code_block import add_code_block_to_doc
except ImportError:
    # 如果 code_block.py 不存在，回退到朴素版本
    def add_code_block_to_doc(doc, code_text, language=None):
        p = doc.add_paragraph()
        pPr = p._p.get_or_add_pPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), 'F5F5F5')
        pPr.append(shd)
        run = p.add_run(code_text)
        run.font.name = 'Courier New'
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(0x26, 0x26, 0x26)


# ============ 个性化定制配置 ============
FONT_NAME = '微软雅黑'           # 全文字体
BODY_FONT_SIZE = 10.5           # 正文字号
TABLE_FONT_SIZE = 9             # 表格字号
MIN_HEADING_SIZE = 12.5          # 最末级标题字号
HEADING_SIZE_STEP = 2            # 每级标题递增字号

# 表情符号映射表
EMOJI_MAP = {
    '👨‍👩‍👦': '[表情：一家人]',
    '👚': '[表情：衣服]',
    '🥗': '[表情：食物]',
    '🏠': '[表情：房子]',
    '🏡': '[表情：房子]',
    '🚴': '[表情：骑车]',
    '🚴‍♂️': '[表情：骑车]',
    '🧋': '[表情：奶茶]',
    '⛹': '[表情：篮球]',
    '⛹️': '[表情：篮球]',
    '🛌': '[表情：睡觉]',
    '🛀': '[表情：洗澡]',
    '💀': '[表情：骷髅]',
    '💞': '[表情：爱心]',
    '👨‍👩‍👦‍👦': '[表情：一家人]',
    '❤️': '[表情：爱心]',
    '🩷': '[表情：爱心]',
    '👨‍👩‍👧': '[表情：一家人]',
    '👨‍👩‍👧‍👦': '[表情：一家人]',
}


def replace_emojis(text):
    """替换文本中的表情符号为文字描述"""
    result = text
    for emoji, replacement in EMOJI_MAP.items():
        result = result.replace(emoji, replacement)
    return result


def calculate_heading_sizes(max_level):
    """
    根据最大标题级别计算各级标题字号
    例如：max_level=3 -> {1: 16.5, 2: 14.5, 3: 12.5}
    """
    sizes = {}
    for level in range(1, max_level + 1):
        # 最末级(min_level) = MIN_HEADING_SIZE
        # 每升一级 +HEADING_SIZE_STEP
        sizes[level] = MIN_HEADING_SIZE + (max_level - level) * HEADING_SIZE_STEP
    return sizes


def set_run_font(run, font_name=None, font_size=None, bold=None, italic=None, color=None):
    """设置run的字体、字号、样式"""
    if font_name:
        run.font.name = font_name
        # 设置中文字体
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    if font_size:
        run.font.size = Pt(font_size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def add_horizontal_rule(doc):
    """在文档中插入水平分割线（模拟 Word 的 --- + 回车效果）"""
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), 'auto')
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p


def set_paragraph_font(para, font_name=None, font_size=None):
    """设置段落默认字体和字号"""
    if font_name or font_size:
        for run in para.runs:
            if font_name:
                run.font.name = font_name
                run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
            if font_size:
                run.font.size = Pt(font_size)


def _find_system_chrome():
    """
    动态检测系统已安装的 Chrome / Edge / Chromium 可执行文件。
    返回可执行文件的绝对路径，找不到则返回 None。
    """
    import platform
    import os as _os

    system = platform.system()
    candidates = []

    if system == 'Windows':
        # 硬编码常见绝对路径，因为 Git Bash 下环境变量可能为空
        local_app = os.getenv('LOCALAPPDATA', '')
        candidates = [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            _os.path.join(local_app, 'Google', 'Chrome', 'Application', 'chrome.exe') if local_app else '',
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        ]
    elif system == 'Darwin':
        candidates = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
            '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
        ]
    else:  # Linux
        candidates = [
            '/usr/bin/google-chrome',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/usr/bin/microsoft-edge',
        ]

    for path in candidates:
        if path and _os.path.isfile(path):
            return path
    return None


def _find_mmdc():
    """
    查找 mmdc 可执行文件，优先级：
    1. skill 目录下 node_modules/.bin/mmdc（或 mmdc.cmd on Windows）
    2. 全局 npm 目录
    3. PATH 查找
    """
    import platform
    import os as _os

    skill_dir = _os.path.dirname(_os.path.abspath(__file__))
    is_windows = platform.system() == 'Windows'
    mmdc_name = 'mmdc.cmd' if is_windows else 'mmdc'

    # 1. skill 目录下本地安装
    local_mmdc = _os.path.join(skill_dir, 'node_modules', '.bin', mmdc_name)
    if _os.path.exists(local_mmdc):
        return local_mmdc

    # 2. 全局 npm 目录
    app_data = os.getenv('APPDATA', '')
    if app_data:
        global_mmdc = _os.path.join(app_data, 'npm', mmdc_name)
        if _os.path.exists(global_mmdc):
            return global_mmdc

    # 3. 兜底 PATH 查找
    return mmdc_name


def _shorten_mmdc_error(stderr_text):
    """
    将 mmdc 的冗长 stderr 提取为单行友好提示。
    mmdc 报错时通常输出完整 Node.js 堆栈，对用户毫无用处。
    策略：提取最后一行 Error: 或错误描述，截断到 120 字。
    """
    if not stderr_text:
        return '未知错误'

    # 常见模式：提取 "Error: xxx" 行
    error_lines = [l for l in stderr_text.splitlines() if 'Error' in l or 'error' in l.lower()]
    if error_lines:
        msg = error_lines[-1].strip()
    else:
        # 兜底：取最后一行非空内容
        non_empty = [l.strip() for l in stderr_text.splitlines() if l.strip()]
        msg = non_empty[-1] if non_empty else '未知错误'

    # 去掉常见前缀噪声
    for prefix in ['Error: ', 'ERROR: ', 'node:internal/modules/cjs/loader: ']:
        if msg.startswith(prefix):
            msg = msg[len(prefix):]

    # 截断超长信息
    if len(msg) > 120:
        msg = msg[:117] + '...'
    return msg


def render_mermaid_to_image(mermaid_code, output_path):
    """将Mermaid代码渲染为图片（本地 mmdc 渲染）"""
    import subprocess
    import json
    import uuid
    import os as _os

    try:
        mermaid_code = mermaid_code.strip()

        # 使用 uuid 避免多进程竞态
        tmp_id = uuid.uuid4().hex[:8]
        mmd_path = _os.path.join(tempfile.gettempdir(), f'mermaid_tmp_{tmp_id}.mmd')

        with open(mmd_path, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)

        skill_dir = _os.path.dirname(_os.path.abspath(__file__))
        mmdc_cmd = _find_mmdc()

        # 构建 mmdc 命令参数
        cmd_args = [mmdc_cmd, '-i', mmd_path, '-o', output_path, '-b', 'white']

        # 动态检测系统 Chrome/Edge，生成临时 Puppeteer 配置
        # 这样 mmdc 就不需要下载 chrome-headless-shell
        chrome_path = _find_system_chrome()
        puppeteer_config_path = None

        if chrome_path:
            config = {
                'executablePath': chrome_path,
                'cacheDirectory': _os.path.join(_os.path.expanduser('~'), '.cache', 'puppeteer'),
            }
            puppeteer_config_path = _os.path.join(tempfile.gettempdir(), f'puppeteerrc_{tmp_id}.json')
            with open(puppeteer_config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f)
            cmd_args.extend(['--puppeteerConfigFile', puppeteer_config_path])

        # 也检查 skill 目录下的静态 .puppeteerrc.json（优先级低于动态检测）
        if not chrome_path:
            static_config = _os.path.join(skill_dir, '.puppeteerrc.json')
            if _os.path.exists(static_config):
                cmd_args.extend(['--puppeteerConfigFile', static_config])

        result = subprocess.run(
            cmd_args,
            capture_output=True,
            timeout=60,
            cwd=skill_dir
        )

        # 清理临时文件
        for tmp_file in [mmd_path, puppeteer_config_path]:
            if tmp_file:
                try:
                    _os.remove(tmp_file)
                except Exception:
                    pass

        if result.returncode == 0 and _os.path.exists(output_path):
            return True
        else:
            stderr_text = result.stderr.decode('utf-8', errors='ignore')
            hint = _shorten_mmdc_error(stderr_text)
            print(f"Mermaid渲染失败: {hint}")
            return False

    except subprocess.TimeoutExpired:
        print("Mermaid渲染失败: 超时（60秒）")
        return False
    except FileNotFoundError:
        print("Mermaid渲染失败: mmdc 未安装，请在 skill 目录执行 npm install")
        return False
    except Exception as e:
        print(f"Mermaid渲染失败: {e}")
        return False


class HTMLTextExtractor(HTMLParser):
    """提取HTML中的纯文本，保留部分格式信息"""
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_blockquote = False
        self.current_alignment = None
        self.current_bold = False
        self.current_italic = False
        self.tag_stack = []
        
    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        attrs_dict = dict(attrs)
        
        if tag == 'blockquote':
            self.in_blockquote = True
            self.text_parts.append(('start_quote', None))
        elif tag == 'strong' or tag == 'b':
            self.current_bold = True
        elif tag == 'em' or tag == 'i':
            self.current_italic = True
        elif tag == 'p':
            style = attrs_dict.get('style', '')
            align_match = re.search(r'text-align:\s*(\w+)', style)
            if align_match:
                align = align_match.group(1)
                if align == 'center':
                    self.current_alignment = 'center'
                elif align == 'right':
                    self.current_alignment = 'right'
        elif tag == 'h1':
            self.text_parts.append(('heading', 1))
        elif tag == 'h2':
            self.text_parts.append(('heading', 2))
        elif tag == 'h3':
            self.text_parts.append(('heading', 3))
        elif tag == 'br':
            self.text_parts.append(('newline', None))
        elif tag == 'div':
            align = attrs_dict.get('align', '')
            if align == 'center':
                self.current_alignment = 'center'
    
    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()
        
        if tag == 'blockquote':
            self.in_blockquote = False
            self.text_parts.append(('end_quote', None))
        elif tag == 'strong' or tag == 'b':
            self.current_bold = False
        elif tag == 'em' or tag == 'i':
            self.current_italic = False
        elif tag == 'p' or tag == 'div':
            if not self.in_blockquote:
                self.current_alignment = None
    
    def handle_data(self, data):
        data = replace_emojis(data)
        if data.strip():
            flags = []
            if self.current_bold:
                flags.append('bold')
            if self.current_italic:
                flags.append('italic')
            if self.current_alignment:
                flags.append(f'align:{self.current_alignment}')
            self.text_parts.append(('text', data, tuple(flags)))
        elif '\n' in data or data == '\n':
            self.text_parts.append(('newline', None))


def strip_html_tags(html_text):
    """移除HTML标签，提取纯文本，并替换表情符号"""
    clean = re.sub(r'<[^>]+>', '', html_text)
    clean = clean.replace('&nbsp;', ' ')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&quot;', '"')
    clean = replace_emojis(clean)
    return clean


def extract_text_with_format(html_text):
    """从HTML中提取文本，保留格式信息"""
    extractor = HTMLTextExtractor()
    try:
        extractor.feed(html_text)
    except:
        pass
    return extractor.text_parts


class ImageManager:
    """图片资源管理器：负责提取、下载、路径解析"""
    
    def __init__(self, input_dir):
        self.input_dir = input_dir
        self.temp_dir = None
        self.image_map = {}  # {original_src: resolved_local_path}
        self._temp_files = []  # 记录临时文件，用于清理
    
    def setup_temp_dir(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp(prefix='md2docx_img_')
        atexit.register(self._cleanup_temp)
    
    def _cleanup_temp(self):
        """清理临时目录"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                print(f"临时文件已清理：{self.temp_dir}")
            except Exception as e:
                print(f"清理临时文件失败：{e}")
    
    def extract_images(self, markdown_content):
        """全局扫描 Markdown，提取所有图片引用"""
        pattern = r'!\[([^\]]*)\]\(\s*([^)\s]+)\s*\)'
        for match in re.finditer(pattern, markdown_content):
            alt_text, img_src = match.groups()
            if img_src not in self.image_map:
                resolved = self._resolve_path(img_src)
                if resolved:
                    self.image_map[img_src] = resolved
                    print(f"图片已提取：{img_src} -> {resolved}")
                else:
                    print(f"图片路径无效：{img_src}")
    
    def _resolve_path(self, src):
        """
        三层路径解析：
        1. HTTP/HTTPS URL → 下载到临时目录
        2. 绝对路径 → 验证存在性
        3. 相对路径 → 相对于 input_dir 解析
        """
        try:
            # 1. URL 下载
            if src.startswith(('http://', 'https://')):
                return self._download_url(src)
            
            # 2. 绝对路径
            if os.path.isabs(src):
                if os.path.exists(src):
                    return src
                else:
                    print(f"绝对路径图片不存在：{src}")
                    return None
            
            # 3. 相对路径（相对于 Markdown 文件所在目录）
            full_path = os.path.join(self.input_dir, src)
            if os.path.exists(full_path):
                return full_path
            else:
                print(f"相对路径图片不存在：{full_path}")
                return None
        
        except Exception as e:
            print(f"解析图片路径失败 {src}: {e}")
            return None
    
    def _download_url(self, url):
        """下载网络图片到临时目录"""
        try:
            if not self.temp_dir:
                self.setup_temp_dir()
            
            # 生成唯一文件名
            parsed = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed.path)
            if not filename or '.' not in filename:
                ext = '.png'
                filename = f'image_{len(self.image_map)}{ext}'
            
            local_path = os.path.join(self.temp_dir, filename)
            
            # 设置 User-Agent，防止某些网站拦截
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(local_path, 'wb') as out_file:
                    out_file.write(response.read())
            
            self._temp_files.append(local_path)
            return local_path
        
        except Exception as e:
            print(f"下载网络图片失败 {url}: {e}")
            return None



def parse_table(lines):
    """解析Markdown表格，过滤分隔行（|---|---|）"""
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        # 跳过分隔行：每个单元格都只含有 - 和 : 和空格
        if all(re.match(r'^[-:\s]+$', cell) for cell in cells if cell):
            continue
        rows.append(cells)
    return rows


# 表格斑马纹颜色（纯灰白交替，不用蓝色）
TABLE_ROW_EVEN_COLOR = 'F2F2F2'   # 浅灰背景（偶数数据行）


def _set_cell_bg(cell, hex_color):
    """给表格单元格设置背景色"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()

    for existing in tcPr.findall(qn('w:shd')):
        tcPr.remove(existing)

    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)


def add_table_to_doc(doc, rows, font_size=None):
    """添加表格到Word文档：表头灰底，数据行白底（符合Markdown默认渲染风格）"""
    if not rows or len(rows) < 1:
        return

    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = 'Table Grid'

    for i, row in enumerate(rows):
        is_header = (i == 0)
        # Markdown表格默认：表头灰底，数据行白底
        if is_header:
            row_color = TABLE_ROW_EVEN_COLOR  # 表头灰底
        else:
            row_color = None  # 数据行白底（无背景）

        for j, cell_text in enumerate(row):
            cell_obj = table.cell(i, j)

            if row_color:
                _set_cell_bg(cell_obj, row_color)

            para = cell_obj.paragraphs[0]
            for run in para.runs:
                run.text = ''

            clean = strip_html_tags(cell_text)
            fs = font_size or TABLE_FONT_SIZE
            nodes = parse_inline(clean)
            render_inline_nodes(para, nodes, FONT_NAME, fs, bold=is_header)

            for run in para.runs:
                run.font.name = FONT_NAME
                try:
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), FONT_NAME)
                except Exception:
                    pass
                run.font.size = Pt(fs)
                run.font.color.rgb = RGBColor(0, 0, 0)


def parse_html_table(html_content):
    """
    解析 HTML 表格，返回 (grid, num_rows, num_cols, merge_cells)。
    
    grid: list[list[str|None]]  二维网格，合并区域用 None 填充
    merge_cells: list[(r1,c1,r2,c2)]  合并区域列表
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')
    if not table:
        return [], 0, 0, []

    rows_data = []          # 每行的 td 原始数据（含 rowspan/colspan）
    for tr in table.find_all('tr'):
        cells = []
        for td in tr.find_all(['td', 'th']):
            rowspan = int(td.get('rowspan', 1))
            colspan = int(td.get('colspan', 1))
            text = td.get_text(separator=' ', strip=True)
            text = replace_emojis(text)
            cells.append({'text': text, 'rowspan': rowspan, 'colspan': colspan})
        rows_data.append(cells)

    if not rows_data:
        return [], 0, 0, []

    # 先算出总列数（表头行通常列数最多）
    num_cols = max(len(r) for r in rows_data)

    # 构建虚拟网格，追踪跨行占用
    num_rows = len(rows_data)
    grid = [[None] * num_cols for _ in range(num_rows)]
    merge_cells = []    # (r1, c1, r2, c2) 合并区域
    occupied = [[False] * num_cols for _ in range(num_rows)]

    for r_idx, cells in enumerate(rows_data):
        col_ptr = 0
        for cell in cells:
            # 找到下一个空闲列
            while col_ptr < num_cols and occupied[r_idx][col_ptr]:
                col_ptr += 1
            if col_ptr >= num_cols:
                break

            rspan = cell['rowspan']
            cspan = cell['colspan']
            text = cell['text']

            # 写入网格
            for dr in range(rspan):
                for dc in range(cspan):
                    rr = r_idx + dr
                    cc = col_ptr + dc
                    if rr < num_rows and cc < num_cols:
                        occupied[rr][cc] = True
                        grid[rr][cc] = text if (dr == 0 and dc == 0) else None

            # 记录合并区域
            if rspan > 1 or cspan > 1:
                merge_cells.append((r_idx, col_ptr, r_idx + rspan - 1, col_ptr + cspan - 1))

            col_ptr += cspan

    return grid, num_rows, num_cols, merge_cells


def _fill_cell(cell_obj, text, font_size, is_header=False):
    """填充单元格文本（复用已有样式逻辑）"""
    # 清除默认内容
    para = cell_obj.paragraphs[0]
    for run in para.runs:
        run.text = ''

    if text:
        nodes = parse_inline(text)
        render_inline_nodes(para, nodes, FONT_NAME, font_size, bold=is_header)

    for run in para.runs:
        run.font.name = FONT_NAME
        try:
            run._element.rPr.rFonts.set(qn('w:eastAsia'), FONT_NAME)
        except Exception:
            pass
        run.font.size = Pt(font_size)
        run.font.color.rgb = RGBColor(0, 0, 0)


def add_html_table_to_doc(doc, html_content, body_size=BODY_FONT_SIZE):
    """解析 HTML 表格（含合并单元格）并添加到 Word 文档"""
    grid, num_rows, num_cols, merge_cells = parse_html_table(html_content)

    if num_rows == 0 or num_cols == 0:
        text = strip_html_tags(html_content)
        if text.strip():
            p = doc.add_paragraph()
            process_formatting(p, text, FONT_NAME, body_size)
        return

    # 创建全尺寸表格
    word_table = doc.add_table(rows=num_rows, cols=num_cols)
    word_table.style = 'Table Grid'

    # 填充所有单元格文本
    for r in range(num_rows):
        for c in range(num_cols):
            text = grid[r][c]
            if text is not None:
                _fill_cell(word_table.cell(r, c), text, body_size, is_header=(r == 0))

    # 处理合并单元格（注意：合并后只保留左上角 cell 对象）
    for (r1, c1, r2, c2) in merge_cells:
        top_left = word_table.cell(r1, c1)
        bottom_right = word_table.cell(r2, c2)
        try:
            top_left.merge(bottom_right)
        except Exception as e:
            print(f"合并单元格失败 [{r1},{c1}]->[{r2},{c2}]: {e}")


def add_html_content_to_doc(doc, html_content, body_size=BODY_FONT_SIZE):
    """处理HTML内容块并添加到文档"""
    # 优先检测并处理 HTML 表格
    if '<table' in html_content.lower():
        add_html_table_to_doc(doc, html_content, body_size)
        return

    parts = extract_text_with_format(html_content)
    
    if not parts:
        text = strip_html_tags(html_content)
        if text.strip():
            p = doc.add_paragraph()
            process_formatting(p, text.strip(), FONT_NAME, body_size)
        return
    
    current_para = None
    quote_mode = False
    # 同一 <p> 段落内累积文本，最后统一用 AST 渲染
    pending_runs = []   # list of (text, bold, italic, align)

    def flush_pending(para):
        """把 pending_runs 渲染到段落，每段用 AST 解析"""
        for text, bold, italic, align in pending_runs:
            if align == 'center':
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif align == 'right':
                para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            nodes = parse_inline(text)
            render_inline_nodes(para, nodes, FONT_NAME, body_size,
                                bold=bold, italic=italic)
        pending_runs.clear()

    for part in parts:
        part_type = part[0]
        
        if part_type == 'start_quote':
            if current_para:
                flush_pending(current_para)
            quote_mode = True
            current_para = doc.add_paragraph()
            current_para.style = 'Quote'

        elif part_type == 'end_quote':
            if current_para:
                flush_pending(current_para)
            quote_mode = False
            current_para = None

        elif part_type == 'heading':
            if current_para:
                flush_pending(current_para)
            level = part[1]
            current_para = doc.add_heading('', level=level - 1 if level > 0 else 0)

        elif part_type == 'text':
            text = part[1]
            flags = part[2] if len(part) > 2 else ()

            if current_para is None:
                if quote_mode:
                    current_para = doc.add_paragraph(style='Quote')
                else:
                    current_para = doc.add_paragraph()

            align_flag = [f for f in flags if f.startswith('align:')]
            align = align_flag[0].split(':')[1] if align_flag else None
            pending_runs.append((text, 'bold' in flags, 'italic' in flags, align))

        elif part_type == 'newline':
            if current_para:
                flush_pending(current_para)
                current_para.add_run('\n')

    if current_para:
        flush_pending(current_para)


# ============================================================
# DOCX → Markdown 转换器
# ============================================================

def html_to_markdown(html):
    """
    将 mammoth 生成的 HTML 转换为 Markdown
    支持：表格、粗体、斜体、换行、div/span
    """
    soup = BeautifulSoup(html, 'html.parser')
    md_parts = []
    
    # 处理表格
    for table in soup.find_all('table'):
        md_parts.append(table_to_markdown(table))
        table.decompose()
    
    # 处理剩余内容
    remaining = str(soup)
    
    # 移除 <p> 标签但保留内容
    remaining = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', remaining, flags=re.DOTALL)
    
    # 处理粗体和斜体
    remaining = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', remaining, flags=re.DOTALL)
    remaining = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', remaining, flags=re.DOTALL)
    remaining = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', remaining, flags=re.DOTALL)
    remaining = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', remaining, flags=re.DOTALL)
    
    # 处理换行符
    remaining = remaining.replace('<br>', '\n')
    remaining = remaining.replace('<br/>', '\n')
    remaining = remaining.replace('<br />', '\n')
    
    # 移除 div/span 标签但保留内容
    remaining = re.sub(r'<div[^>]*>(.*?)</div>', r'\1\n', remaining, flags=re.DOTALL)
    remaining = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', remaining, flags=re.DOTALL)
    
    # 移除所有剩余标签
    clean_text = re.sub(r'<[^>]+>', '', remaining)
    
    # 处理 HTML 实体
    clean_text = clean_text.replace('&nbsp;', ' ')
    clean_text = clean_text.replace('&lt;', '<')
    clean_text = clean_text.replace('&gt;', '>')
    clean_text = clean_text.replace('&amp;', '&')
    clean_text = clean_text.replace('&quot;', '"')
    
    # 替换表情符号
    clean_text = replace_emojis(clean_text)
    
    # 合并结果
    if md_parts:
        md_parts.append(clean_text.strip())
        return '\n\n'.join(md_parts)
    else:
        return clean_text.strip()


def table_to_markdown(table):
    """将 HTML 表格转换为 Markdown 表格"""
    rows = []
    for tr in table.find_all('tr'):
        cells = []
        for cell in tr.find_all(['td', 'th']):
            # 提取单元格内的纯文本（包括换行）
            cell_text = cell.get_text(separator=' ', strip=True)
            cell_text = replace_emojis(cell_text)
            cells.append(cell_text)
        if cells:
            rows.append(cells)
    
    if not rows:
        return ''
    
    # 计算最大列数
    max_cols = max(len(row) for row in rows)
    
    # 补齐缺失的列
    for row in rows:
        while len(row) < max_cols:
            row.append('')
    
    # 构建 Markdown 表格
    md_lines = []
    
    # 表头
    header = rows[0]
    md_lines.append('| ' + ' | '.join(header) + ' |')
    
    # 分隔行
    md_lines.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
    
    # 数据行
    for row in rows[1:]:
        md_lines.append('| ' + ' | '.join(row) + ' |')
    
    return '\n'.join(md_lines)


def docx_to_md(input_file, output_file):
    """转换 Word 文档到 Markdown"""
    print(f"正在转换：{input_file} -> {output_file}")
    
    # 使用 mammoth 转换为 HTML
    with open(input_file, 'rb') as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value
        
        # 输出警告信息（但不影响转换）
        if result.messages:
            for msg in result.messages:
                print(f"警告：{msg.message}")
    
    # 将 HTML 转换为 Markdown
    markdown = html_to_markdown(html)
    
    # 保存 Markdown 文件
    with open(output_file, 'w', encoding='utf-8') as md_file:
        md_file.write(markdown)
    
    print(f"转换完成：{input_file} -> {output_file}")
    print(f"输出文件大小：{len(markdown)} 字符，{len(markdown.splitlines())} 行")


def md_to_docx(input_file, output_file):
    """转换Markdown文件到Word文档"""
    with open(input_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    doc = Document()
    
    # 清零 Normal 样式的段前段后间距，防止每段后自动多一行
    style = doc.styles['Normal']
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after  = Pt(0)
    
    lines = md_content.strip().split('\n')
    input_dir = os.path.dirname(os.path.abspath(input_file))
    
    # 【新增】初始化图片管理器并提取所有图片
    img_manager = ImageManager(input_dir)
    img_manager.extract_images(md_content)
    
    # 第一遍扫描：检测最大标题级别
    max_heading_level = 0
    for line in lines:
        heading_match = re.match(r'^(#{1,6})\s+', line)
        if heading_match:
            level = len(heading_match.group(1))
            max_heading_level = max(max_heading_level, level)
    
    # 计算各级标题字号
    heading_sizes = calculate_heading_sizes(max_heading_level) if max_heading_level > 0 else {1: 14.5}
    print(f"检测到 {max_heading_level} 级标题")
    print(f"标题字号: {heading_sizes}")
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 处理HTML标签开头的行
        if line.strip().startswith('<') and not line.strip().startswith('```'):
            html_block = []
            html_block.append(line)
            
            if line.strip().startswith('<blockquote') or line.strip().startswith('<div'):
                depth = 1
                i += 1
                while i < len(lines) and depth > 0:
                    html_block.append(lines[i])
                    if '</blockquote>' in lines[i]:
                        depth -= 1
                    if '<blockquote' in lines[i] and '</blockquote>' not in lines[i]:
                        depth += 1
                    if lines[i].strip().startswith('</div>') and html_block[-1].strip() == '</div>':
                        if '</div>' in '\n'.join(html_block[:-1]):
                            pass
                        depth -= 1
                    i += 1
                
                html_content = '\n'.join(html_block)
                add_html_content_to_doc(doc, html_content)
                continue
            
            elif line.strip().startswith('<h') or line.strip().startswith('<p') or line.strip().startswith('<div'):
                add_html_content_to_doc(doc, line)
                i += 1
                continue
        
        # 处理Markdown引用块
        if line.startswith('> ') and not line.strip().startswith('>&gt;'):
            quote_lines = []
            while i < len(lines) and (lines[i].startswith('> ') or lines[i].startswith('>')):
                q_line = lines[i]
                if q_line.startswith('> '):
                    q_line = q_line[2:]
                elif q_line.startswith('>'):
                    q_line = q_line[1:]
                quote_lines.append(q_line.strip())
                i += 1

            full_quote = '\n'.join(quote_lines)
            if full_quote.strip().startswith('<'):
                add_html_content_to_doc(doc, full_quote)
            else:
                # 多行引用：每行一个段落，全部用 Quote 样式，行内格式走 AST 解析
                for j, ql in enumerate(quote_lines):
                    p = doc.add_paragraph()
                    p.style = 'Quote'
                    if ql:
                        process_formatting(p, ql, FONT_NAME, BODY_FONT_SIZE)
                        for run in p.runs:
                            run.font.color.rgb = RGBColor(0, 0, 0)
                    else:
                        # 空行也保留引用段落
                        run = p.add_run('')
                        run.font.color.rgb = RGBColor(0, 0, 0)
            continue
        
        # 处理代码块（包括Mermaid）
        if line.strip().startswith('```'):
            code_language = line.strip()[3:].lower()
            
            code_content = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_content.append(lines[i])
                i += 1
            
            code_text = '\n'.join(code_content)
            
            if code_language == 'mermaid':
                mermaid_code = code_text
                temp_dir = tempfile.gettempdir()
                img_counter = len([f for f in os.listdir(temp_dir) if f.startswith('mermaid_')])
                img_path = os.path.join(temp_dir, f'mermaid_{img_counter}.png')
                
                print(f"正在渲染Mermaid图表...")
                if render_mermaid_to_image(mermaid_code, img_path):
                    try:
                        from PIL import Image as PILImage
                        img = PILImage.open(img_path)
                        orig_w, orig_h = img.size  # 单位：像素
                        img.close()
                        
                        # 页面可用尺寸（单位：英寸）
                        # A4 纸 8.27" x 11.69"，左右页边距约 1"，上下约 1"
                        MAX_WIDTH_INCHES = 6.0   # 最大可用宽度
                        MAX_HEIGHT_INCHES = 8.0  # 最大可用高度（留余量给段落间距）
                        
                        # 计算最终宽度：优先满足宽度限制，高度超限则按高度缩放
                        # 如果宽度超限 → 按宽度缩放（高度等比缩小）
                        # 如果高度超限 → 按高度缩放（宽度等比缩小）
                        # 96 DPI 是 Word 默认图片分辨率
                        final_width_inches = orig_w / 96  # 像素转英寸
                        
                        if final_width_inches > MAX_WIDTH_INCHES:
                            # 宽度超标，按宽度缩放
                            final_width_inches = MAX_WIDTH_INCHES
                            print(f"  → 宽度超标，已缩放至 {MAX_WIDTH_INCHES}\"")
                        elif orig_h / 96 > MAX_HEIGHT_INCHES:
                            # 高度超标，按高度缩放
                            final_width_inches = orig_w * (MAX_HEIGHT_INCHES / orig_h)
                            print(f"  → 高度超标，已缩放")
                        
                        p = doc.add_paragraph()
                        run = p.add_run()
                        run.add_picture(img_path, width=Inches(final_width_inches))
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        print(f"Mermaid图表渲染成功 (原始: {orig_w}x{orig_h}px)")
                    except ImportError:
                        # 没有 Pillow，回退到默认宽度
                        p = doc.add_paragraph()
                        run = p.add_run()
                        run.add_picture(img_path, width=Inches(5.5))
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        print(f"Mermaid图表渲染成功")
                    except Exception as e:
                        print(f"添加图片失败: {e}")
                        p = doc.add_paragraph()
                        p.add_run('[Mermaid图表]')
                else:
                    p = doc.add_paragraph()
                    p.add_run('[Mermaid图表渲染失败，原代码如下:]')
                    run = p.add_run(code_text)
                    set_run_font(run, 'Courier New', 9)
            else:
                # 使用 Pygments 语法高亮（带行号和彩色 token）
                add_code_block_to_doc(doc, code_text, language=code_language)
            
            i += 1
            continue
        
        # 处理表格
        if line.strip().startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            
            rows = parse_table(table_lines)
            add_table_to_doc(doc, rows, TABLE_FONT_SIZE)
            continue
        
        # 处理水平分割线 ---
        if re.match(r'^[-*_]{3,}\s*$', line.strip()):
            add_horizontal_rule(doc)
            i += 1
            continue

        # 处理标题
        heading_match = re.match(r'^(#{1,6})\s+(.*)', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            text = strip_html_tags(text)
            
            # 添加标题并设置字号
            p = doc.add_heading('', level=level-1 if level > 0 else 0)
            
            # 用 AST 渲染标题文字（支持粗体等行内格式）
            heading_size = heading_sizes.get(level, MIN_HEADING_SIZE)
            nodes = parse_inline(text)
            render_inline_nodes(p, nodes, FONT_NAME, heading_size, bold=True)

            # 强制覆盖 Word 内置样式颜色为黑色，并统一字体字号
            for run in p.runs:
                run.font.name = FONT_NAME
                try:
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), FONT_NAME)
                except Exception:
                    pass
                run.font.size = Pt(heading_size)
                run.bold = True
                run.font.color.rgb = RGBColor(0, 0, 0)
            
            i += 1
            continue
        
        # 处理列表
        if re.match(r'^[-*]\s+', line):
            list_text = line[2:].strip()
            p = doc.add_paragraph(style='List Bullet')
            process_formatting(p, list_text, FONT_NAME, BODY_FONT_SIZE)
            for run in p.runs:
                run.font.color.rgb = RGBColor(0, 0, 0)
            i += 1
            continue
        
        # 处理图片（使用 ImageManager 预处理的映射表）
        img_match = re.search(r'!\[([^\]]*)\]\(([^\)]+)\)', line)
        if img_match:
            alt_text = img_match.group(1)
            img_src = img_match.group(2)
            
            # 从映射表获取已解析的本地路径
            img_path = img_manager.image_map.get(img_src)
            
            if img_path and os.path.exists(img_path):
                try:
                    p = doc.add_paragraph()
                    run = p.add_run()
                    run.add_picture(img_path, width=Inches(4))
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    # 如果有 alt 文本，添加标题
                    if alt_text.strip():
                        cap = doc.add_paragraph(alt_text.strip())
                        cap.style = 'Caption'
                        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                except Exception as e:
                    print(f"添加图片失败：{e}")
                    p = doc.add_paragraph()
                    run = p.add_run(f'[图片：{alt_text}]')
                    set_run_font(run, FONT_NAME, BODY_FONT_SIZE)
            else:
                # 图片缺失时保留占位提示
                print(f"图片缺失：{alt_text} (源：{img_src})")
                p = doc.add_paragraph()
                run = p.add_run(f'[图片缺失：{alt_text}]')
                set_run_font(run, FONT_NAME, BODY_FONT_SIZE, italic=True)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1
            continue

        
        # 处理链接
        link_match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', line)
        if link_match:
            line = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'\1: \2', line)
        
        # 处理空行：跳过，不额外加段落（段间距由 Normal 样式控制）
        if not line.strip():
            i += 1
            continue
        
        # 处理普通段落（直接走 AST，保留 **粗体** 等行内格式）
        raw_line = strip_html_tags(line) if line.strip().startswith('<') else line
        if raw_line.strip():
            p = doc.add_paragraph()
            process_formatting(p, raw_line, FONT_NAME, BODY_FONT_SIZE)
            # 强制黑色，防止继承样式颜色
            for run in p.runs:
                run.font.color.rgb = RGBColor(0, 0, 0)
        
        i += 1
    
    doc.save(output_file)
    print(f"转换完成: {input_file} -> {output_file}")


# ============================================================
# AST 行内元素解析器
# 节点类型: text / bold / italic / bold_italic / code / link
# ============================================================

# ============================================================
# AST 行内元素解析器
# 节点类型：text / bold / italic / bold_italic / code / link
# ============================================================

class InlineNode:
    """行内 AST 节点"""
    def __init__(self, node_type, content, children=None, href=None):
        self.type = node_type       # 'text'|'bold'|'italic'|'bold_italic'|'code'|'link'
        self.content = content      # 叶子节点文本（非叶子为 None）
        self.children = children or []  # 子节点列表
        self.href = href            # link 节点的 URL


def parse_inline(text):
    """
    将行内 Markdown 文本解析为 AST 节点列表。
    支持：**bold**、*italic*、***bold+italic***、`code`、[link](url)
    核心思路：
      1. 扫描 token（标记符 / 普通文本）
      2. 用栈维护嵌套关系
      3. 遇到匹配的闭合标记符，弹出栈帧并生成节点
    """
    tokens = _tokenize_inline(text)
    nodes, _ = _parse_tokens(tokens, 0, end_marker=None)
    return nodes


def _tokenize_inline(text):
    """
    词法分析：将字符串切成 token 列表
    每个 token: (type, value)
      type: 'marker'（*** ** * `）| 'link_open'（[）| 'link_mid'（](）| 'link_close'（)）| 'text'
    """
    # 匹配模式：先匹配长 marker，再匹配短 marker，防止 ** 被切成两个 *
    pattern = re.compile(
        r'(\*{3}|\*{2}|\*|`|\[|\]\(|(?<=\]\().*?(?=\))|\))',
    )
    tokens = []
    pos = 0
    # 改用手动扫描来正确处理 [text](url) 结构
    i = 0
    while i < len(text):
        # 检测链接 [label](url)
        link_m = re.match(r'\[([^\[\]]*?)\]\(([^)]*?)\)', text[i:])
        if link_m:
            tokens.append(('link', link_m.group(1), link_m.group(2)))
            i += link_m.end()
            continue
        # 检测行内代码 `code`
        code_m = re.match(r'`([^`]+?)`', text[i:])
        if code_m:
            tokens.append(('code', code_m.group(1), None))
            i += code_m.end()
            continue
        # 检测 ***
        if text[i:i+3] == '***':
            tokens.append(('marker', '***', None))
            i += 3
            continue
        # 检测 **
        if text[i:i+2] == '**':
            tokens.append(('marker', '**', None))
            i += 2
            continue
        # 检测 *
        if text[i] == '*':
            tokens.append(('marker', '*', None))
            i += 1
            continue
        # 普通文本：累积到下一个特殊字符
        j = i + 1
        while j < len(text) and text[j] not in ('*', '`', '['):
            # 检测是否到链接开始
            if text[j] == '[':
                break
            j += 1
        tokens.append(('text', text[i:j], None))
        i = j
    return tokens


def _parse_tokens(tokens, start, end_marker):
    """
    递归解析 token 列表，返回 (节点列表, 消耗到的位置)
    end_marker: 期望的结束标记符，None 表示解析到末尾
    """
    nodes = []
    i = start
    text_buf = ''

    def flush_text():
        nonlocal text_buf
        if text_buf:
            nodes.append(InlineNode('text', text_buf))
            text_buf = ''

    while i < len(tokens):
        tok_type, tok_val, tok_extra = tokens[i]

        if tok_type == 'text':
            text_buf += tok_val
            i += 1
            continue

        if tok_type == 'code':
            flush_text()
            nodes.append(InlineNode('code', tok_val))
            i += 1
            continue

        if tok_type == 'link':
            flush_text()
            nodes.append(InlineNode('link', tok_val, href=tok_extra))
            i += 1
            continue

        if tok_type == 'marker':
            marker = tok_val

            # 如果是期待的结束标记，停止递归
            if marker == end_marker:
                flush_text()
                return nodes, i + 1

            # 尝试作为开启标记，找到对应的闭合位置
            close_idx = _find_close(tokens, i + 1, marker)

            if close_idx is None:
                # 找不到闭合，当作普通文本
                text_buf += marker
                i += 1
                continue

            # 找到闭合，递归解析内部
            flush_text()
            inner_nodes, _ = _parse_tokens(tokens, i + 1, end_marker=marker)

            if marker == '***':
                node = InlineNode('bold_italic', None, children=inner_nodes)
            elif marker == '**':
                node = InlineNode('bold', None, children=inner_nodes)
            elif marker == '*':
                node = InlineNode('italic', None, children=inner_nodes)
            else:
                node = InlineNode('text', marker)

            nodes.append(node)
            # 跳到闭合标记之后
            i = close_idx + 1
            continue

        i += 1

    flush_text()
    return nodes, i


def _find_close(tokens, start, marker):
    """在 tokens[start:] 中查找第一个与 marker 匹配的闭合 token"""
    depth = 0
    for i in range(start, len(tokens)):
        t, v, _ = tokens[i]
        if t == 'marker':
            if v == marker:
                if depth == 0:
                    return i
                depth -= 1
            elif v in ('***', '**', '*'):
                depth += 1
    return None


def render_inline_nodes(para, nodes, font_name, font_size, bold=False, italic=False):
    """
    将 AST 节点列表渲染到 Word 段落。
    bold/italic 参数用于父节点传递样式（嵌套）
    """
    for node in nodes:
        if node.type == 'text':
            if node.content:
                run = para.add_run(node.content)
                set_run_font(run, font_name, font_size, bold=bold, italic=italic)
                run.font.color.rgb = RGBColor(0, 0, 0)

        elif node.type == 'bold':
            render_inline_nodes(para, node.children, font_name, font_size,
                                bold=True, italic=italic)

        elif node.type == 'italic':
            render_inline_nodes(para, node.children, font_name, font_size,
                                bold=bold, italic=True)

        elif node.type == 'bold_italic':
            render_inline_nodes(para, node.children, font_name, font_size,
                                bold=True, italic=True)

        elif node.type == 'code':
            run = para.add_run(node.content)
            set_run_font(run, 'Courier New', font_size - 0.5)
            # 经典代码块效果：深灰背景 + 深灰文字
            run.font.color.rgb = RGBColor(0x4E, 0x4E, 0x4E)
            # 加背景色（Word shd 元素）
            rPr = run._r.get_or_add_rPr()
            shd_el = OxmlElement('w:shd')
            shd_el.set(qn('w:val'), 'clear')
            shd_el.set(qn('w:color'), 'auto')
            shd_el.set(qn('w:fill'), 'D9D9D9')    # 浅灰背景
            rPr.append(shd_el)

        elif node.type == 'link':
            # 链接：显示文字，不插超链接（Word超链接复杂，暂显文本）
            run = para.add_run(node.content)
            set_run_font(run, font_name, font_size, bold=bold, italic=italic)
            run.underline = True
            run.font.color.rgb = RGBColor(0, 0, 0)


def process_formatting(para, text, font_name, font_size):
    """
    将行内 Markdown 文本通过 AST 解析后渲染到段落。
    替代原来的正则逐行匹配，处理嵌套和边界更健壮。
    """
    nodes = parse_inline(text)
    render_inline_nodes(para, nodes, font_name, font_size)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python md2docx.py <input.md> <output.docx>')
        print('       python md2docx.py <input.docx> <output.md>')
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(input_file):
        print(f'错误：输入文件不存在 {input_file}')
        sys.exit(1)
    
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 自动识别文件类型并调用相应的转换函数
    input_ext = os.path.splitext(input_file)[1].lower()
    
    if input_ext == '.md':
        # Markdown → Word
        md_to_docx(input_file, output_file)
    elif input_ext == '.docx':
        # Word → Markdown
        docx_to_md(input_file, output_file)
    else:
        print(f'错误：不支持的文件类型 {input_ext}')
        print('支持的文件类型：.md, .docx')
        sys.exit(1)
