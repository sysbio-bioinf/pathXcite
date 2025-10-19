import json
import os
import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from app.pathxcite import PathXCite
from app.setup_utils.initial_page import InitialPage
from app.utils import resource_path


def rewrite_default_config(folder_path: str) -> None:
    """Create a default config.json file in the specified folder path.

    Args:
        folder_path (str): The path to the folder where the config file will be created.
    """
    config_data = {
        "project_folder": folder_path,
        "api_email": None,
        "api_key": None
    }
    config_path = os.path.join(folder_path, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)


def launch_pathxcite(folder_path: str) -> None:
    """Launch the PathXCite application with the specified project folder.

    Args:
        folder_path (str): The path to the project folder.
    """
    config_path = os.path.join(folder_path, "config.json")
    config_data = {}
    if not os.path.exists(config_path):
        rewrite_default_config(folder_path)

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    if not isinstance(config_data, dict):
        print("Invalid config format.")
        config_data = {}
        rewrite_default_config(folder_path)
        config_data = json.load(f)

    if "project_folder" not in config_data or "api_email" not in config_data or "api_key" not in config_data:
        print("Missing required config fields.")
        config_data = {}
        rewrite_default_config(folder_path)
        config_data = json.load(f)

    main_window = PathXCite(folder_path, config_data)
    main_window.show()


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)

        app.setWindowIcon(
            QIcon(str(resource_path("assets/icons/pathXciteIcon002.svg"))))

        setup = InitialPage(exit_on_open=False)
        setup.setWindowTitle("PathXCite - Project Setup")
        setup.resize(600, 220)

        setup.open_requested.connect(launch_pathxcite)

        setup.show()
        sys.exit(app.exec_())

    except Exception as e:
        print(f"ERROR: {e}")
