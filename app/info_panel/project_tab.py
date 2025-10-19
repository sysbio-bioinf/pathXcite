"""Tab for displaying project files of the current project folder in a tree view"""

# --- Standard Library Imports ---
import os

# -- Third Party Imports ---
from PyQt5.QtCore import QFileInfo, QModelIndex, QPoint, Qt
from PyQt5.QtWidgets import QFileSystemModel, QHeaderView, QMenu, QTreeView


# --- Public Classes ---
class ProjectFolderView(QTreeView):
    """ A tab for displaying project files in a tree view """

    def __init__(self, folder_path: str, main_app=None):
        """Initializes the project folder view.

        Args:
            folder_path: Path to the project folder.
            main_app: Reference to the main application (for opening files).
        """
        super().__init__()
        self.main_app = main_app  # Store reference to main app if needed
        self.folder_path = folder_path
        self.model = QFileSystemModel()
        self.model.setRootPath(os.path.expanduser(self.folder_path))
        self.setModel(self.model)
        self.setRootIndex(self.model.index(
            os.path.expanduser(self.folder_path)))
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setHeaderHidden(False)

        # Configure column resizing
        self.header().setSectionResizeMode(QHeaderView.Stretch)
        self.header().setStretchLastSection(False)

        # Enable right-click context menu for column visibility
        self.header().setContextMenuPolicy(Qt.CustomContextMenu)
        self.header().customContextMenuRequested.connect(self.show_column_menu)

        # Connect the click signal
        self.doubleClicked.connect(self.handle_item_click)

    def handle_item_click(self, index: QModelIndex) -> None:
        """Handle double-click on file items

        Args:
            index: The QModelIndex of the clicked item.
        """
        if not index.isValid():
            return

        file_path = self.model.filePath(index)
        file_info = QFileInfo(file_path)

        if file_info.isFile():
            if file_info.suffix().lower() in ["txt", "html", "md", "csv", "tsv", "json", "xml"]:
                self.main_app.open_file_in_browser(file_path)
            # if the file is a png or jpg, open it in the default image viewer
            elif file_info.suffix().lower() in ["png", "jpg", "jpeg"]:

                self.main_app.open_image_viewer(file_path)

    def set_folder_path(self, folder_path: str) -> None:
        """Updates the folder path
        Args:
            folder_path: New folder path to set.
        """
        self.folder_path = folder_path
        self.model.setRootPath(os.path.expanduser(self.folder_path))
        self.setRootIndex(self.model.index(
            os.path.expanduser(self.folder_path)))

    def show_column_menu(self, pos: QPoint) -> None:
        """ Show a context menu to enable/disable columns 
        Args:
            pos: Position to show the menu.
        """
        menu = QMenu(self)
        for i in range(self.model.columnCount()):
            column_name = self.model.headerData(i, Qt.Horizontal)
            action = menu.addAction(column_name)
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(i))
            action.triggered.connect(
                lambda checked, i=i: self.toggle_column(i, checked))
        menu.exec_(self.header().mapToGlobal(pos))

    def toggle_column(self, column: int, checked: bool) -> None:
        """ Toggle visibility of a column
         Args:
            column: Column index to toggle.
            checked: Whether the column should be shown.
        """
        self.setColumnHidden(column, not checked)
