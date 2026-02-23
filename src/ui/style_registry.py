"""
Centralized CSS Style Registry for VNNotes.
Contains reusable CSS fragments and style templates to ensure theme consistency.
"""

class StyleRegistry:
    # --- Paging & Massive Documents ---
    PAGING_MESSAGE = (
        "<br><p style='color:gray; text-align:center; font-style:italic; margin: 20px 0;'>"
        "--- Content Paged for Performance. Scroll for more ---"
        "</p>"
    )
    
    PAGING_END_MESSAGE = (
        "<p style='color:gray; text-align:center; font-style:italic; margin: 20px 0;'>"
        "--- End of Document ---"
        "</p>"
    )

    PAGING_FOCUS_HEADER_TEMPLATE = (
        "<p style='color:#888; text-align:center; background: {bg}; padding: 4px; border-radius: 4px;'>"
        "--- Showing lines {start} to {end} of {total} ---"
        "</p>"
    )

    # --- Images & Multimedia ---
    IMAGE_DEFAULT_STYLE = "max-width: 100%; border-radius: 4px; border: 1px solid {border};"
    
    # --- Teleprompter (Glassmorphism) ---
    TELEPROMPTER_CONTAINER = """
        background: {bg_alpha};
        border-radius: 20px;
        border: 1px solid {border_alpha};
    """
    
    # --- Sidebar Search & Tree ---
    SIDEBAR_SEARCH_STYLE = """
        background: {surface}; 
        color: {text}; 
        border: 1px solid {border}; 
        border-radius: 6px; 
        padding: 4px 8px; 
        margin: 6px; 
    """

    SEARCH_HIGHLIGHT_COLOR = "#FFFF00"

    @staticmethod
    def format_style(template, **kwargs):
        """Helper to inject theme variables into a style template."""
        return template.format(**kwargs)
