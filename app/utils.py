"""General utility functions for the application"""

# --- Standard Library Imports ---
import re
import sys
from io import StringIO
from pathlib import Path

# --- Third Party Imports ---
import numpy as np
import pandas as pd


# --- Public Functions ---
def read_data_structure(file_path: str):
    """
    Reads a data structure from a file, replacing inf with np.inf.

    Args:
        file_path (str): Path to the file containing the data structure.

    Returns:
        The data structure with inf values replaced by np.inf.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        data = file.read()

    # Replace `inf` with `np.inf` for compatibility
    data = re.sub(r'\binf\b', 'np.inf', data)
    data = re.sub(r'\b-inf\b', '-np.inf', data)

    try:
        # Using eval with numpy, assuming data is trusted
        return eval(data, {"np": np})
    except Exception as e:

        return None


def resource_path(relative_path: str) -> Path:
    """ Get absolute path to resource

    Args:
        relative_path (str): Relative path to the resource file.

    Returns:
        Path: Absolute path to the resource file.
    """
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        # Use the directory of the main entry script
        base_path = Path(sys.argv[0]).resolve().parent

    full_path = base_path / relative_path

    return full_path


def dataframe_to_tsv(df: pd.DataFrame) -> str:
    """Convert a pandas DataFrame to a TSV string.

    Args:
        df (pd.DataFrame): The DataFrame to convert.

    Returns:
        str: The TSV representation of the DataFrame."""
    output = StringIO()
    df.to_csv(output, sep='\t', index=False)
    return output.getvalue()


def get_default_html_svg(icon_abs_path: str, width=35, height=35,
                         message: str = "Please start enrichment process to get insights into enriched pathways.") -> str:
    """
    Generate an HTML string for QWebEngineView with a local SVG icon.

    Args: 
        icon_abs_path (str): OS-specific absolute path to the SVG file (e.g. from resource_path()).
        message (str): Message text to display under the icon.

    Returns:
        str: HTML string containing the SVG icon and message.
    """
    svg_content = open(icon_abs_path, encoding="utf-8").read()

    return f"""
    <!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Select a Document</title>
<style>
body {{
    font-family: 'Poppins', sans-serif;
    text-align: center;
    margin: 50px;
    background: white;/*linear-gradient(135deg, #fdfbfb, #ebedee);*/
    display: flex;
    justify-content: center;
    align-items: center;
    height: 75vh;
}}
.message-container {{
    padding: 20px 30px;
    border-radius: 12px;
    background: white;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
    display: inline-block;
    max-width: 400px;
    transition: transform 0.2s ease-in-out;
}}
.message-container:hover {{ transform: scale(1.05); }}
.message {{
    font-size: 13px;
    font-weight: 400;
    color: #2c3e50;
}}
.icon {{
    display: block;        /* keeps it above the text */
    width: {width}px;           /* smaller width */
    height: {height}px;          /* constrain height */
    margin: 0 auto 12px;   /* center horizontally, add space below */
}}
.icon svg {{
    width: 100%;           /* make the <svg> scale inside the box */
    height: 100%;
}}
</style>
</head>
<body>
<div class="message-container">
    <!-- non-overlapping svg with message -->
  <div class="icon">{svg_content}</div>
  <p class="message">{message}</p>
</div>
</body>
</html>
    """
