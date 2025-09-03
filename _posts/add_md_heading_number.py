import re

# 中文编号映射（支持前 20 个）
chinese_numbers = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
                   '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十']

def remove_existing_number(title_line, pattern):
    """去除已有编号，如 '## 一、XXX' -> '## XXX'"""
    match = re.match(pattern, title_line)
    if match:
        return f"{match.group(1)} {match.group(3)}"
    return title_line

def add_heading_numbers(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    sec2_count = 0
    sec3_count = 0
    sec4_count = 0
    new_lines = []

    for line in lines:
        # 检查并移除旧的编号（##）
        line = remove_existing_number(line, r'^(##)(\s+)[一二三四五六七八九十十二三四五六七八九十]{1,3}、\s*(.+)')
        # 检查并移除旧的编号（###）
        line = remove_existing_number(line, r'^(###)(\s+)[0-9]+[\.、]\s*(.+)')
        # 清除 #### 的字母编号（如：#### (a) xxx）
        line = remove_existing_number(line, r'^(####)(\s+)\([a-z]\)\s*(.+)')
        if line.startswith('## '):
            # 添加中文编号
            prefix = f"{chinese_numbers[sec2_count]}、"
            content = line.strip().split(' ', 1)[1]
            new_lines.append(f"## {prefix}{content}\n")
            sec2_count += 1
            sec3_count = 0  # 重置小节编号
        elif line.startswith('### '):
            # 添加数字编号
            prefix = f"{sec3_count + 1}."
            content = line.strip().split(' ', 1)[1]
            new_lines.append(f"### {prefix} {content}\n")
            sec3_count += 1
            sec4_count = 0  # 新三级标题出现时重置四级计数
        elif line.startswith('#### '):
            # 添加英文字母编号：a, b, c...
            letter = chr(ord('a') + sec4_count)
            prefix = f"({letter})"
            content = line.strip().split(' ', 1)[1]
            new_lines.append(f"#### {prefix} {content}\n")
            sec4_count += 1
        else:
            new_lines.append(line)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"✅ 标题编号已添加，输出文件：{output_file}")

# 使用方式
if __name__ == '__main__':
    filepath = '_posts\\'
    input_md = '2025-09-02-树莓派实现无线打印.md'# 输入文件名
    input_md = filepath + input_md
    # output_md = 'your_markdown_numbered.md' # 输出文件名
    output_md = input_md
    add_heading_numbers(input_md, output_md)
