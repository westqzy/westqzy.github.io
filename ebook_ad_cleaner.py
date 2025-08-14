#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ebook_ad_cleaner.py
清理电子书中的广告水印（支持 .txt 和 .epub）

用法：
  python ebook_ad_cleaner.py 输入文件 输出文件

示例：
  python ebook_ad_cleaner.py novel.txt novel_clean.txt
  python ebook_ad_cleaner.py book.epub book_clean.epub
"""
from __future__ import annotations
import sys, re, zipfile, io, os
from pathlib import Path
# 规则示例：把“应老师” -> “杜思颖”
NAME_REPLACEMENTS = [
    ("应老师", "杜思颖", True, False),
]

def apply_name_replacements(text: str) -> str:
    import re, unicodedata
    text = unicodedata.normalize("NFKC", text)
    SEP = r"(?:\s|&nbsp;|&#160;|<[^>]*>)*"   # 纯TXT可改成 r"\s*"
    VAR = {"应":"应應", "师":"师師", "師":"师師"}

    def fuzzy_cjk(name: str) -> str:
        parts = []
        for ch in name:
            parts.append(f"[{VAR[ch]}]" if ch in VAR else re.escape(ch))
        return SEP.join(parts)

    for old, new, is_cjk, ignore_case in NAME_REPLACEMENTS:
        if is_cjk:
            pat = re.compile(rf"{fuzzy_cjk(old)}(?:们)?")
            text = pat.sub(new, text)
        else:
            flags = re.IGNORECASE if ignore_case else 0
            text = re.sub(rf"(?<!\w){re.escape(old)}(?!\w)", new, text, flags=flags)
    return text

# 1) 需要清理的特定站点标记（可自行扩充）
SITE_PATTERNS = [
    # 更通用：热点电子书 + （任意或空）+ 免费(电子书|小说)(在线)?(阅读|下载)
    r"热点电子书\s*[（(]\s*[^)）]*\s*[)）]\s*(?:免费)?\s*(?:电子书|小说)\s*(?:在线)?\s*(?:阅读|下载)?",
    r"热点电子书\s*(?:免费)?\s*(?:电子书|小说)\s*(?:在线)?\s*(?:阅读|下载)?",

    r"热点电子书\s*（?\s*W?w?w?\.?r?d?txt\.com\s*）?\s*免费电子书下载",
    r"热点电子书\s*\(W?w?w?\.?r?d?txt\.com\)\s*免费电子书下载",
    r"霸气书库\s*（?\s*W?w?w?\.?87book\.com\s*）?\s*txt电子书下载",
    r"霸气书库\s*\(W?w?w?\.?87book\.com\)\s*txt电子书下载",
    r"\bW?w?w?\.?rdtxt\.com\b",
    r"\bW?w?w?\.?87book\.com\b",
    r"电子书下载\s*$",
    r"(?mi)^[^\n]*?(?:电子书|txt(?![A-Za-z0-9_]))[^\n]*$",
]

# 2) 常见“推广/水印行”的判定关键字（行内出现这些词+域名/联系方式时会整行删除）
AD_KEYWORDS = [
    "免费", "电子书", "下载", "TXT", "txt", "小说", "阅读", "最新章节",
    "手机", "wap", "书城", "书库", "整理", "制作", "分享", "转载", "打赏",
    "关注", "公众号", "微信", "扣扣", "QQ", "群", "求收藏", "求月票"
]

# 3) 判定一行是否为“带推广倾向”的短行（可删除）
DOMAIN_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/\S*)?"
)
CONTACT_RE = re.compile(
    r"(?:Q{2}|QQ|微信|VX|vx|V信|微信群|公众号|公[-\s]*众[-\s]*号|微博|@[a-zA-Z0-9_]+)"
)

# 4) 通用清洗：去掉零宽字符、BOM、过量空白
ZW_RE = re.compile(r"[\u200B\u200C\u200D\uFEFF]")

def strip_bom(text: str) -> str:
    if text.startswith("\ufeff"):
        return text.lstrip("\ufeff")
    return text

def looks_like_ad_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    # 很多广告行比较短
    if len(s) <= 120 and (DOMAIN_RE.search(s) or CONTACT_RE.search(s)):
        if any(k in s for k in AD_KEYWORDS):
            return True
    return False

def build_replace_regex() -> re.Pattern:
    # 将所有特定站点模式合并
    parts = [f"(?:{p})" for p in SITE_PATTERNS]
    # 允许括号的中英文与空白差异
    rx = re.compile("|".join(parts), flags=re.IGNORECASE)
    return rx

SPECIFIC_RE = build_replace_regex()

def clean_text_content(text: str) -> str:
    # 统一换行
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = strip_bom(text)
    text = ZW_RE.sub("", text)
    # 先清特定短语
    text = SPECIFIC_RE.sub("", text)
    # 去除清理后遗留的空括号
    text = re.sub(r"[（(]\s*[)）]", "", text)
    # 行级过滤
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        # 再清一次特定短语（考虑混排）
        line2 = SPECIFIC_RE.sub("", line)
        # 强力规则：包含“热点电子书”且含“免费”并伴随“电子书/小说”则整行删除
        if ("热点电子书" in line2 and "免费" in line2 and ("电子书" in line2 or "小说" in line2)):
            continue
        if looks_like_ad_line(line2):
            continue
        # 常见“本站、来源”类提示
        if len(line2.strip()) <= 40 and any(k in line2 for k in ("来源", "整理", "来自", "首发", "首发于")) and DOMAIN_RE.search(line2):
            continue
        cleaned.append(line2)
    out = "\n".join(cleaned)
    # 合并过量空行
    out = re.sub(r"\n{3,}", "\n\n", out).strip() + "\n"
    return out

def process_txt(in_path: Path, out_path: Path):
    # 猜测编码，优先 utf-8，失败则退回 gb18030
    data = None
    for enc in ("utf-8", "gb18030", "big5"):
        try:
            data = in_path.read_text(encoding=enc)
            break
        except Exception:
            continue
    if data is None:
        raise RuntimeError("无法解码TXT，请手动指定编码后再试。")
    cleaned = clean_text_content(data)
    out = apply_name_replacements(cleaned)
    out_path.write_text(out, encoding="utf-8")
    print(f"[OK] TXT 清理完成：{out_path}")

def process_epub(in_path: Path, out_path: Path):
    with zipfile.ZipFile(in_path, "r") as zin, zipfile.ZipFile(out_path, "w") as zout:
        # 按EPUB规范，mimetype需存储不压缩
        for info in zin.infolist():
            data = zin.read(info.filename)
            fname = info.filename
            # 保留原时间戳/权限尽量不改
            zinfo = zipfile.ZipInfo(filename=fname, date_time=info.date_time)
            zinfo.external_attr = info.external_attr
            # mimetype 文件需要 STORE
            if fname == "mimetype":
                zinfo.compress_type = zipfile.ZIP_STORED
                zout.writestr(zinfo, data)
                continue

            # 文本类文件：xhtml/html/htm/xml/opf/ncx/css 进行替换
            ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
            if ext in ("xhtml", "html", "htm", "xml", "opf", "ncx", "css"):
                try:
                    txt = data.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        txt = data.decode("gb18030")
                    except UnicodeDecodeError:
                        # 非文本或编码异常，原样复制
                        zinfo.compress_type = zipfile.ZIP_DEFLATED
                        zout.writestr(zinfo, data)
                        continue
                cleaned = clean_text_content(txt)
                zinfo.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(zinfo, cleaned.encode("utf-8"))
            else:
                # 资源文件原样拷贝
                zinfo.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(zinfo, data)
    print(f"[OK] EPUB 清理完成：{out_path}")

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    if not in_path.exists():
        print(f"输入文件不存在：{in_path}")
        sys.exit(2)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    suffix = in_path.suffix.lower()
    if suffix == ".txt":
        process_txt(in_path, out_path)
    elif suffix == ".epub":
        process_epub(in_path, out_path)
    else:
        print("暂不支持该格式，请先转换为 .txt 或 .epub 再处理。")
        sys.exit(3)

if __name__ == "__main__":
    main()
