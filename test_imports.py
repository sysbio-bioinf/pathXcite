""" Tests all necessary imports for pathXcite to run. """
import base64
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import partial
import hashlib
from html import escape
import inspect
from io import StringIO
import itertools
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import sqlite3
import time
import traceback 
import sys
from typing import Tuple, List, Dict, Optional
from urllib.parse import quote
import uuid
import weakref
import xml.etree.ElementTree as ET


# put in requirements
import numpy as np
import pandas as pd
import requests
from scipy.stats import fisher_exact, hypergeom
# import sip
from statsmodels.stats.multitest import multipletests


from PyQt5.QtCore import pyqtSignal, QObject, QModelIndex, QAbstractListModel, QVariant, QSortFilterProxyModel, QTimer, QDateTime, Qt, QMetaObject, Q_ARG, pyqtSlot, QSize, QUrl, QPoint, QFileInfo, QRegularExpression, QThread, QRectF, QEvent, QRunnable, QCoreApplication, QThreadPool, QMutex, QWaitCondition

from PyQt5.QtGui import QColor, QFont, QPainter, QFontMetrics, QTextCursor, QRegularExpressionValidator, QDesktopServices, QPainter, QGuiApplication, QIcon

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QMessageBox, QFileDialog, QHBoxLayout, QComboBox, QCheckBox, QTableWidgetItem, QSplitter,  QTableWidget, QHeaderView, QLabel, QMenuBar, QMenu, QStackedWidget, QLineEdit, QPushButton, QScrollArea, QFrame, QSizePolicy, QApplication, QStyledItemDelegate, QListView, QStyleOptionViewItem, QStyle, QStackedLayout, QToolButton, QGridLayout, QLayout, QDialog, QListWidget, QInputDialog, QGraphicsDropShadowEffect, QWidgetAction, QListWidgetItem, QAction, QTextEdit, QTreeView, QFileSystemModel, QProgressBar, QFormLayout, QToolBar, QSizePolicy, QWidget, QTreeWidget, QTreeWidgetItem

from PyQt5.QtSvg import QSvgWidget, QSvgRenderer

from PyQt5 import QtWidgets, QtCore, QtGui, sip

from PyQt5.QtWebEngineWidgets import QWebEngineProfile, QWebEnginePage, QWebEngineView

