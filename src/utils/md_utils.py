try:
    import markdown
    from markdownify import markdownify as md
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False
import re
import logging

logger = logging.getLogger(__name__)

def markdown_to_html(text):
    """
    Converts Markdown to HTML. Uses 'markdown' library if available,
    otherwise falls back to a basic regex implementation.
    """
    if not text:
        return ""

    if not HAS_LIBS:
        logger.warning("Markdown library not found. Using basic regex fallback.")
        return _basic_markdown_to_html(text)

    # Professional extensions for "smart" features - pruned for speed
    extensions = [
        'extra',           # Tables, custom attributes, etc.
        'nl2br',           # Newline to BR
        'sane_lists',      # More expected list behavior
        'smarty'           # Better quotes/dashes
    ]

    try:
        # Convert to HTML
        html = markdown.markdown(text, extensions=extensions)
        
        # Batch style injection for speed on large notes
        return _apply_vnnotes_styles(html)
    except Exception as e:
        logger.error(f"Error in professional Markdown conversion: {e}")
        return _basic_markdown_to_html(text)

def html_to_markdown(html):
    """
    Converts HTML back to Markdown. Uses 'markdownify' if available,
    otherwise falls back to a basic regex implementation.
    """
    if not html:
        return ""

    # DIAMOND-STANDARD: Aggressively strip internal CSS and Head meta-data.
    # This prevents Qt's auto-generated <style> block from leaking into plain text.
    html = re.sub(r'<head.*?>.*?</head>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style.*?>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    if not HAS_LIBS:
        logger.warning("Markdownify library not found. Using basic regex fallback.")
        return _basic_html_to_markdown(html)

    try:
        # markdownify options for clean output
        md_text = md(html, 
                     heading_style="ATX", 
                     newline_style="BACKSLASH",
                     bullets="-",
                     strip=['script', 'style'])

        return _cleanup_markdown(md_text).strip()
    except Exception as e:
        logger.error(f"Error in professional HTML to Markdown conversion: {e}")
        return _basic_html_to_markdown(html)

def _basic_markdown_to_html(text):
    """Basic regex-based fallback for MD to HTML."""
    if not text: return ""
    lines = text.splitlines()
    html_lines = []
    in_list = False
    for line in lines:
        line = line.strip()
        if re.match(r'^(\*\*\*|---|_ _ _)$', line):
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append("<hr>")
            continue
        header_match = re.match(r'^(#{1,3})\s+(.*)', line)
        if header_match:
            if in_list: html_lines.append("</ul>"); in_list = False
            level = len(header_match.group(1))
            sizes = {1: "24pt", 2: "18pt", 3: "14pt"}
            size = sizes.get(level, "14pt")
            html_lines.append(f'<h{level} style="font-size: {size}; font-weight: bold;">{_format_inline(line[level:].strip())}</h{level}>')
            continue
        list_match = re.match(r'^([-*+])\s+(.*)', line)
        if list_match:
            if not in_list: html_lines.append('<ul style="margin-left: 20px;">'); in_list = True
            html_lines.append(f'<li>{_format_inline(list_match.group(2))}</li>')
            continue
        else:
            if in_list: html_lines.append("</ul>"); in_list = False
        if line: html_lines.append(f'<p>{_format_inline(line)}</p>')
        else: html_lines.append("<br>")
    if in_list: html_lines.append("</ul>")
    return "".join(html_lines)

def _basic_html_to_markdown(html):
    """Basic regex-based fallback for HTML to MD."""
    html = re.sub(r'<h1.*?>(.*?)</h1>', r'# \1\n\n', html, flags=re.I)
    html = re.sub(r'<h2.*?>(.*?)</h2>', r'## \1\n\n', html, flags=re.I)
    html = re.sub(r'<b>(.*?)</b>', r'**\1**', html, flags=re.I)
    html = re.sub(r'<i>(.*?)</i>', r'*\1*', html, flags=re.I)
    html = re.sub(r'<p>(.*?)</p>', r'\1\n\n', html, flags=re.I | re.S)
    html = re.sub(r'<.*?>', '', html)
    return html.strip()

def _format_inline(text):
    text = re.sub(r'(\*\*|__)(.*?)\1', r'<b>\2</b>', text)
    text = re.sub(r'(\*|_)(.*?)\1', r'<i>\2</i>', text)
    return text

def _apply_vnnotes_styles(html):
    """Injects specific font sizes for headers to match the editor's expected style."""
    styles = {
        '<h1>': '<h1 style="font-size: 24pt; font-weight: bold;">',
        '<h2>': '<h2 style="font-size: 18pt; font-weight: bold;">',
        '<h3>': '<h3 style="font-size: 14pt; font-weight: bold;">',
        '<ul>': '<ul style="margin-left: 20px;">',
        '<ol>': '<ol style="margin-left: 20px;">'
    }
    for tag, styled_tag in styles.items():
        html = html.replace(tag, styled_tag)
    return html

def _cleanup_markdown(text):
    """Removes excessive empty lines and unescapes certain characters."""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.replace("&nbsp;", " ")
    return text
