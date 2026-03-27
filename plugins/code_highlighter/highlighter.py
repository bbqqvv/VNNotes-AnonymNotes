import logging
import re
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import Qt, QRegularExpression

class UniversalHighlighter(QSyntaxHighlighter):
    """
    A senior-level, multi-language syntax highlighter with high-contrast 
    professional themes and stateful multiline support.
    """
    def __init__(self, parent=None, is_dark=True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.highlighting_rules = []
        self._initialize_formats()
        self._setup_rules()

    def _initialize_formats(self):
        """Sets up high-contrast professional palettes."""
        if self.is_dark:
            # Dracula-inspired high-contrast dark palette
            self.colors = {
                "keyword": "#ff79c6",    # Pink
                "flow": "#8be9fd",       # Cyan
                "declaration": "#50fa7b", # Green
                "type": "#8be9fd",        # Cyan (italic)
                "string": "#f1fa8c",      # Yellow
                "number": "#bd93f9",      # Purple
                "comment": "#6272a4",     # Muted Blue/Gray
                "function": "#50fa7b",    # Green
                "class": "#8be9fd",       # Cyan
                "operator": "#ffb86c",    # Orange
                "bracket": "#f8f8f2",     # White
                "decorator": "#f1fa8c",   # Yellow
                "tag": "#ff79c6",         # Pink
                "attribute": "#50fa7b"    # Green
            }
        else:
            # High-contrast light palette (Solarized-inspired)
            self.colors = {
                "keyword": "#d33682",    # Magenta
                "flow": "#268bd2",       # Blue
                "declaration": "#859900", # Green
                "type": "#2aa198",        # Cyan
                "string": "#b58900",      # Yellow/Brown
                "number": "#6c71c4",      # Violet
                "comment": "#93a1a1",     # Gray
                "function": "#268bd2",    # Blue
                "class": "#cb4b16",       # Orange
                "operator": "#dc322f",    # Red
                "bracket": "#586e75",     # Dark Gray
                "decorator": "#b58900",   # Yellow
                "tag": "#d33682",         # Magenta
                "attribute": "#859900"    # Green
            }

        # Pre-build formats for performance
        self.formats = {}
        for key, color_hex in self.colors.items():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color_hex))
            if key == "type":
                fmt.setFontItalic(True)
            self.formats[key] = fmt

    def _setup_rules(self):
        """Defines all regex rules for common language constructs."""
        
        # 1. Keywords & Flow Control
        keywords = [
            "break", "continue", "return", "yield", "await", "async",
            "try", "except", "finally", "with", "import", "from", "as",
            "True", "False", "None", "null", "undefined", "static", "void",
            "public", "private", "protected", "new", "this", "super"
        ]
        flow_control = ["if", "else", "elif", "while", "for", "in", "do", "switch", "case", "default"]
        declarations = ["def", "class", "function", "let", "const", "var", "interface", "type", "struct", "enum"]

        for word in keywords:
            self.highlighting_rules.append((re.compile(f"\\b{word}\\b"), self.formats["keyword"]))
        for word in flow_control:
            self.highlighting_rules.append((re.compile(f"\\b{word}\\b"), self.formats["flow"]))
        for word in declarations:
            self.highlighting_rules.append((re.compile(f"\\b{word}\\b"), self.formats["declaration"]))

        # 2. Literals (Numbers & Strings)
        # Numbers: Hex (0x), Binary (0b), Floats (1.23)
        self.highlighting_rules.append((re.compile(r"\b0x[0-9a-fA-F]+\b|\b0b[01]+\b|\b\d+(\.\d+)?([eE][+-]?\d+)?\b"), self.formats["number"]))
        
        # Simple Strings (Single line)
        self.highlighting_rules.append((re.compile(r'"[^"\\\n]*(\\.[^"\\\n]*)*"'), self.formats["string"]))
        self.highlighting_rules.append((re.compile(r"'[^'\\\n]*(\\.[^'\\\n]*)*'"), self.formats["string"]))

        # 3. Operators & Brackets
        self.highlighting_rules.append((re.compile(r"[\+\-\*\/\%\=\!\<\>\|\&\^\~\?]"), self.formats["operator"]))
        self.highlighting_rules.append((re.compile(r"[\(\)\[\]\{\}]"), self.formats["bracket"]))

        # 4. Classes and Functions (Declarations and Calls)
        # Function Calls: print()
        self.highlighting_rules.append((re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b(?=\s*\()"), self.formats["function"]))
        # Class names: Capitalized words
        self.highlighting_rules.append((re.compile(r"\b[A-Z][A-Za-z0-9_]*\b"), self.formats["class"]))

        # 5. Decorators & Special Tags
        # Python Decorators
        self.highlighting_rules.append((re.compile(r"@[A-Za-z0-9_\.]+"), self.formats["decorator"]))
        # HTML Tags: <div style="...">
        self.highlighting_rules.append((re.compile(r"<\/?\w+"), self.formats["tag"]))
        self.highlighting_rules.append((re.compile(r"\b\w+(?=\s*=\s*[\"'])"), self.formats["attribute"]))

        # 6. Comments (Single line)
        self.highlighting_rules.append((re.compile(r"#.*"), self.formats["comment"]))
        self.highlighting_rules.append((re.compile(r"//.*"), self.formats["comment"]))

        # 7. Multiline Patterns (Stored for highlightBlock)
        self.multiline_rules = [
            # Pattern, start_state, end_state, format
            (re.compile(r"/\*"), re.compile(r"\*/"), 1, self.formats["comment"]),
            (re.compile(r"'''"), re.compile(r"'''"), 2, self.formats["string"]),
            (re.compile(r'"""'), re.compile(r'"""'), 3, self.formats["string"]),
        ]

    def highlightBlock(self, text):
        """Applies highlighting rules with stateful multiline tracking."""
        # 1. Apply standard rules
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

        # 2. Apply stateful multiline rules (Comments/Block Strings)
        self.setCurrentBlockState(0)
        
        start_index = 0
        if self.previousBlockState() > 0:
            start_index = 0
            
        # We only support one active multiline state per block for simplicity
        # But we need to check which state we carried over
        prev_state = self.previousBlockState()
        
        for start_rx, end_rx, state_id, fmt in self.multiline_rules:
            if prev_state == state_id:
                # We are continuing a multiline block
                match = end_rx.search(text)
                if not match:
                    # Still in the same state
                    self.setFormat(0, len(text), fmt)
                    self.setCurrentBlockState(state_id)
                    return # Done with this block
                else:
                    # End of multiline block found
                    self.setFormat(0, match.end(), fmt)
                    start_index = match.end()
            
            # Look for NEW multiline blocks in the remaining text
            while start_index < len(text):
                start_match = start_rx.search(text, start_index)
                if not start_match:
                    break
                
                end_match = end_rx.search(text, start_match.end())
                if not end_match:
                    # Carry state to next block
                    self.setFormat(start_match.start(), len(text) - start_match.start(), fmt)
                    self.setCurrentBlockState(state_id)
                    return
                else:
                    # Complete block within this line
                    self.setFormat(start_match.start(), end_match.end() - start_match.start(), fmt)
                    start_index = end_match.end()
