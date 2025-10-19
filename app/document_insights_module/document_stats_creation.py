"""Generates HTML statistics for the document insights module"""

# --- Standard Library Imports ---
import json
import random
from typing import Any

# --- Local Imports ---
from app.utils import get_default_html_svg, resource_path

# --- Public Functions ---


def generate_html(db_manager: Any, pmc_id: str | None) -> str:
    """ 
    Generate HTML for the Statistics tab using Chart.js 

    Args:
        db_manager (Any): The database manager instance.
        pmc_id (str | None): The PMC ID to filter the statistics.

    Returns:
        str: The generated HTML content.
    """

    head: str = _get_head_html()
    if not str(pmc_id).startswith("PMC"):
        pmc_id: str | None = None

    if pmc_id is not None:
        # Fetch pmc id for pubmed_id
        pubmed_id: str | None = db_manager.get_pubmed_id_by_pmc_id(pmc_id)

        # annotations represents a dictionary with the keys being the passage numbers
        # and the values being the annotations for that passage
        passage_annotation_data: dict = db_manager.get_passage_data_by_pmc_and_pubmed(
            pmc_id, pubmed_id)
        passage_ann_data_only_gene: dict = db_manager.get_passage_data_by_pmc_and_pubmed_only_gene(
            pmc_id, pubmed_id)
        annotations, passage_types = passage_annotation_data[
            "annotations"], passage_annotation_data["passage_types"]
        annotations_only_gene, _ = passage_ann_data_only_gene[
            "annotations"], passage_ann_data_only_gene["passage_types"]

        if annotations:
            passage_ranges_json: str = _get_passage_ranges(passage_types)

            # for each value, calculate the average number of annotations per passage
            annotations_per_passage = 0
            passage_number_to_annotation_count: dict = {}
            if annotations_only_gene is not None:
                annotations_per_passage = _get_average_annotation_count(
                    annotations_only_gene)
                passage_number_to_annotation_count = {
                    k: len(v) for k, v in annotations_only_gene.items()}

            passage_number_to_annotation_count_json = json.dumps(
                passage_number_to_annotation_count)

            section_chart_html: str = _generate_section_chart_html(head, annotations_per_passage,
                                                                   passage_number_to_annotation_count_json,
                                                                   passage_ranges_json)

            return section_chart_html

    error_html = """
        <!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PubTator3 Annotations</title>
<style>
body {
    font-family: 'Poppins', sans-serif;
    text-align: center;
    margin: 50px;
    background: linear-gradient(135deg, #fdfbfb, #ebedee);
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
}
.message-container {
    padding: 20px 30px;
    border-radius: 12px;
    background: white;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
    display: inline-block;
    max-width: 400px;
    transition: transform 0.2s ease-in-out;
}
.message-container:hover {
    transform: scale(1.05);
}
.message {
    font-size: 20px;
    font-weight: 600;
    color: #2c3e50;
}
.icon {
    font-size: 40px;
    color: #e74c3c;
    margin-bottom: 10px;
}
</style>
</head>
<body>
<div class="message-container">
<div class="icon">⚠️</div>
<p class="message">No PubTator3 annotations available for this document!</p>
</div>
</body>
</html>
        """
    return error_html

# --- Private Functions ---


def _get_average_annotation_count(annotations_only_gene):
    """
    Calculates the average number of annotations per passage.

    Args:
        annotations_only_gene (dict): A dictionary where each key represents
        a passage and each value is a list of annotations for that passage.

    Returns:
        float: The average number of annotations per passage. 
        Returns 0 if the input dictionary is empty.
    """
    v_sum = sum(len(v) for v in annotations_only_gene.values())

    annotations_per_passage = v_sum / \
        len(annotations_only_gene) if annotations_only_gene else 0
    return annotations_per_passage


def _get_ranges(data_dict: dict) -> list[tuple[int, int, str]]:
    """
    This function takes a dictionary with keys as indices and values as section names.
    It identifies the ranges where each section name appears consecutively.

    Args:
        data_dict: Dictionary where keys are indices and values are section names.

    Returns:
        List of tuples (start_index, end_index, value)
    """
    sorted_keys: list[int] = sorted(
        data_dict.keys())  # Ensure the keys are in increasing order
    ranges: list[tuple[int, int, str]] = []

    start: int = sorted_keys[0]  # Initialize the start of the first range
    current_value: str = data_dict[start]

    for i in range(1, len(sorted_keys)):
        key: int = sorted_keys[i]

        # If the value changes, store the previous range and reset the start
        if data_dict[key] != current_value:
            ranges.append((start, sorted_keys[i-1], current_value))
            start: int = key
            current_value: str = data_dict[key]

    # Add the last range
    ranges.append((start, sorted_keys[-1], current_value))

    return ranges


def _get_passage_ranges(passage_types: dict[int, str]) -> str:
    """
    Generate JSON representation of passage ranges with colors for visualization.

    Args:
        passage_types: Dictionary mapping passage indices to their section types.

    Returns:
        JSON representation of passage ranges with colors.
    """
    passage_ranges: list[tuple[int, int, str]] = _get_ranges(passage_types)
    # Predefined section colors
    section_colors = {
        "TITLE": "rgba(255, 99, 132, 0.2)",   # Red
        "ABSTRACT": "rgba(54, 162, 235, 0.2)",  # Blue
        "INTRO": "rgba(75, 192, 192, 0.2)",    # Teal
        "METHODS": "rgba(255, 206, 86, 0.2)",  # Yellow
        "TABLE": "rgba(153, 102, 255, 0.2)",   # Purple
        "RESULTS": "rgba(255, 159, 64, 0.2)",  # Orange
        "FIG": "rgba(0, 0, 0, 0.2)",           # Black/Grey
        "DISCUSS": "rgba(201, 203, 207, 0.2)",  # Light Grey
        "CONCL": "rgba(46, 204, 113, 0.2)",    # Green
        "REF": "rgba(127, 140, 141, 0.2)"      # Dark Grey
    }

    section_colors = {
        "TITLE": "rgba(255, 69, 105, 0.3)",   # Strong Red
        "ABSTRACT": "rgba(30, 144, 255, 0.3)",  # Bright Blue
        "INTRO": "rgba(32, 178, 170, 0.3)",    # Vibrant Teal
        "METHODS": "rgba(255, 193, 7, 0.3)",  # Deep Yellow
        "TABLE": "rgba(138, 43, 226, 0.3)",   # Rich Purple
        "RESULTS": "rgba(255, 140, 0, 0.3)",  # Strong Orange
        "FIG": "rgba(0, 0, 0, 0.3)",          # True Black
        "DISCUSS": "rgba(255, 105, 180, 0.3)",  # Hot Pink (to avoid grey)
        "CONCL": "rgba(46, 204, 113, 0.3)",    # Bold Green
        "REF": "rgba(127, 140, 141, 0.2)"      # Grey for References ONLY
    }

    # Function to generate random unique colors
    def generate_random_rgba():
        return f"rgba({random.randint(50, 255)}, {random.randint(50, 255)}, {random.randint(50, 255)}, 0.2)"

    # Identify unknown section types and assign unique colors
    unique_unknown_colors: dict[str, str] = {}
    for _, _, label in passage_ranges:
        if label not in section_colors and label not in unique_unknown_colors:
            unique_unknown_colors[label] = generate_random_rgba()

    # Merge known and unknown colors
    final_section_colors = {**section_colors, **unique_unknown_colors}

    # Convert passage_ranges to JSON
    passage_ranges_json = json.dumps([
        {"start": start, "end": end, "label": label,
            "color": final_section_colors[label]}
        for start, end, label in passage_ranges
    ])
    return passage_ranges_json


def _generate_section_chart_html(head: str, annotations_per_passage: float,
                                 passage_number_to_annotation_count: dict[int, int],
                                 passage_ranges_json: str) -> str:
    """
    Generate HTML for Section Annotations chart.

    Args:
        head: HTML head section.
        annotations_per_passage: Average number of annotations per passage.
        passage_number_to_annotation_count: Mapping of passage numbers to annotation counts.
        passage_ranges_json: JSON representation of passage ranges with colors.

    Returns:
        Complete HTML string for the chart.
    """
    if annotations_per_passage == 0:
        icon_abs_path = icon_abs_path = str(
            resource_path("assets/icons/no_genes_found.svg"))
        return get_default_html_svg(icon_abs_path=icon_abs_path,
                                    width=40, height=40,
                                    message="No gene annotations found for this article.")

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    {head}

        <body>   
    <p><b>Average annotations per Section:</b> {round(annotations_per_passage, 2)}</p>

    <!-- Introducing a floating barrier and 100px of space-->
    <!--<div style="clear: both; margin-top: 100px;"></div>-->
    <div class="chart-container">
        <h3>Gene Annotations per Section</h3>
        <canvas id="passageAnnotationChart"></canvas>
    </div>

    <!-- Legend container -->
    <div id="legend-container" style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 50px;"></div>

    <!-- Load Chart.js and the Annotation Plugin -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@1.2.1"></script>

    <script>
        // Ensure the plugin is correctly registered
        Chart.register(window['chartjs-plugin-annotation']);


        var passageNumberToAnnotationCount = {passage_number_to_annotation_count};
        var passageRanges = {passage_ranges_json};

        // Create background annotations for each section
        var annotations = passageRanges.reduce((acc, range, index) => {{
            acc[`box${{index}}`] = {{
                type: 'box',
                xMin: range.start,
                xMax: range.end,
                backgroundColor: range.color,
                borderWidth: 0
            }};
            return acc;
        }}, {{}});

        // Render the line chart
        var ctx = document.getElementById('passageAnnotationChart').getContext('2d');
        var passageAnnotationChart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: Object.keys(passageNumberToAnnotationCount),
                datasets: [{{
                    label: 'Annotations per Section',
                    data: Object.values(passageNumberToAnnotationCount),
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    annotation: {{
                        annotations: annotations
                    }}
                }},
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: 'Section Number'
                        }}
                    }},
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Annotation Count'
                        }}
                    }}
                }}
            }}
        }});

        // Generate the legend dynamically (only unique section types)
        function createLegend(passageRanges) {{
            var legendContainer = document.getElementById("legend-container");
            legendContainer.innerHTML = ""; // Clear previous legend

            // Extract unique section labels and colors
            var uniqueSections = {{}};
            passageRanges.forEach(range => {{
                if (!uniqueSections[range.label]) {{
                    uniqueSections[range.label] = range.color;
                }}
            }});

            // Create legend items for each unique section
            Object.entries(uniqueSections).forEach(([label, color]) => {{
                var legendItem = document.createElement("div");
                legendItem.style.display = "flex";
                legendItem.style.alignItems = "center";
                legendItem.style.gap = "5px";

                var colorBox = document.createElement("div");
                colorBox.style.width = "15px";
                colorBox.style.height = "15px";
                colorBox.style.backgroundColor = color;
                colorBox.style.border = "1px solid #000";

                var labelText = document.createElement("span");
                labelText.innerText = label;

                legendItem.appendChild(colorBox);
                legendItem.appendChild(labelText);
                legendContainer.appendChild(legendItem);
            }});
        }}

        // Call the function to generate the legend

        createLegend(passageRanges);
    </script>


    </body>
    </html>
    """


def _get_head_html() -> str:
    """ Generate the HTML head section for statistics pages.
    It contains meta tags, title, font links, Chart.js script, and CSS styles.
    Returns:
        str: HTML head section as a string.
    """

    return """<head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Statistics</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {
                font-family: 'Roboto', sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #ffffff;
            }
            h2, h3 {
                color: #333;
            }
            .styled-table {
                border-collapse: collapse;
                margin: 25px 0;
                font-size: 0.9em;
                min-width: 400px;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
            }
            .styled-table thead tr {
                background-color: #009879;
                color: #ffffff;
                text-align: left;
            }
            .styled-table th, .styled-table td {
                padding: 12px 15px;
            }
            .styled-table tbody tr {
                border-bottom: 1px solid #dddddd;
            }
            .styled-table tbody tr:nth-of-type(even) {
                background-color: #f3f3f3;
            }
            .styled-table tbody tr:last-of-type {
                border-bottom: 2px solid #009879;
            }
            .chart-container {
                width: 100%;
                max-width: 600px;
                height: 400px;
                margin: 0 auto;
            }
        </style>
    </head>"""
