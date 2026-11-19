from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QSpinBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QStatusBar, QHeaderView, QAbstractItemView
)
from renamer_core import build_plan, execute_plan, undo_last, RenameError


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Shuffle Renamer")
        self.resize(1020, 680)
        self.setMinimumSize(760, 500)
        self.folder = None
        self.plan = []
        self._build_ui()
        self.statusBar().showMessage("Готово. Выберите папку и загрузите файлы.")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(13)

        title = QLabel("File Shuffle Renamer")
        title.setObjectName("title")
        subtitle = QLabel("Случайная нумерация файлов в выбранной папке")
        subtitle.setObjectName("subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Папка:"))
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Выберите папку с файлами…")
        self.folder_edit.setReadOnly(True)
        folder_row.addWidget(self.folder_edit, 1)
        browse = QPushButton("Обзор")
        browse.clicked.connect(self.choose_folder)
        folder_row.addWidget(browse)
        layout.addLayout(folder_row)

        settings = QGridLayout()
        settings.setHorizontalSpacing(12)
        settings.setVerticalSpacing(8)
        self.start_spin = QSpinBox(); self.start_spin.setRange(-999999999, 999999999); self.start_spin.setValue(1)
        self.step_spin = QSpinBox(); self.step_spin.setRange(-999999999, 999999999); self.step_spin.setValue(1)
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("Например, File_")
        self.suffix_edit = QLineEdit("_")
        self.suffix_edit.setPlaceholderText("Например, _ или +")
        settings.addWidget(QLabel("Начальный номер"), 0, 0)
        settings.addWidget(self.start_spin, 0, 1)
        settings.addWidget(QLabel("Шаг"), 0, 2)
        settings.addWidget(self.step_spin, 0, 3)
        settings.addWidget(QLabel("Текст перед числом"), 1, 0)
        settings.addWidget(self.prefix_edit, 1, 1)
        settings.addWidget(QLabel("Текст после числа"), 1, 2)
        settings.addWidget(self.suffix_edit, 1, 3)
        layout.addLayout(settings)

        actions = QHBoxLayout()
        self.load_btn = QPushButton("Загрузить файлы")
        self.shuffle_btn = QPushButton("Перемешать")
        self.reshuffle_btn = QPushButton("Перемешать заново")
        self.load_btn.clicked.connect(self.load_files)
        self.shuffle_btn.clicked.connect(self.shuffle)
        self.reshuffle_btn.clicked.connect(self.shuffle)
        actions.addWidget(self.load_btn); actions.addWidget(self.shuffle_btn); actions.addWidget(self.reshuffle_btn)
        layout.addLayout(actions)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Исходное имя", "Новое имя"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.count_label = QLabel("Файлов: 0")
        bottom.addWidget(self.count_label)
        bottom.addStretch(1)
        self.undo_btn = QPushButton("Отменить последнее переименование")
        self.rename_btn = QPushButton("Переименовать файлы")
        self.undo_btn.clicked.connect(self.undo)
        self.rename_btn.clicked.connect(self.rename)
        bottom.addWidget(self.undo_btn); bottom.addWidget(self.rename_btn)
        layout.addLayout(bottom)
        self.setStatusBar(QStatusBar())

        self.setStyleSheet("""
            QMainWindow, QWidget { background: #f4f6fa; color: #202938; font-size: 10pt; }
            QLabel#title { font-size: 22pt; font-weight: 700; color: #17243a; }
            QLabel#subtitle { color: #66748a; padding-bottom: 5px; }
            QLineEdit, QSpinBox, QTableWidget { background: white; border: 1px solid #d8deea; border-radius: 7px; padding: 7px; }
            QTableWidget { gridline-color: #e8ecf2; }
            QHeaderView::section { background: #e9eef6; border: 0; padding: 9px; font-weight: 600; }
            QPushButton { background: #e5eaf3; border: 0; border-radius: 7px; padding: 9px 14px; font-weight: 600; }
            QPushButton:hover { background: #d7e1f1; }
            QPushButton:pressed { background: #c7d5ea; }
            QPushButton#primary { background: #2864d7; color: white; }
            QPushButton#primary:hover { background: #1f55bd; }
        """)
        self.rename_btn.setObjectName("primary")

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.folder = Path(folder)
            self.folder_edit.setText(folder)
            self.load_files()

    def load_files(self):
        if not self.folder or not self.folder.is_dir():
            QMessageBox.information(self, "Папка не выбрана", "Сначала выберите папку.")
            return
        self.shuffle()

    def shuffle(self):
        if not self.folder:
            QMessageBox.information(self, "Папка не выбрана", "Сначала выберите папку.")
            return
        try:
            self.plan = build_plan(self.folder, self.start_spin.value(), self.step_spin.value(),
                                   self.prefix_edit.text(), self.suffix_edit.text())
            self._show_plan()
            self.statusBar().showMessage("Порядок перемешан. Имена на диске пока не изменены.")
        except RenameError as e:
            QMessageBox.warning(self, "Невозможно подготовить переименование", str(e))

    def _show_plan(self):
        self.table.setRowCount(len(self.plan))
        for row, item in enumerate(self.plan):
            self.table.setItem(row, 0, QTableWidgetItem(item.source.name))
            self.table.setItem(row, 1, QTableWidgetItem(item.target.name))
        self.count_label.setText(f"Файлов: {len(self.plan)}")

    def rename(self):
        if not self.plan:
            QMessageBox.information(self, "Нет файлов", "Загрузите файлы и подготовьте перемешивание.")
            return
        answer = QMessageBox.question(
            self, "Подтверждение",
            f"Переименовать {len(self.plan)} файлов в папке?\nСодержимое файлов не изменяется.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            log = execute_plan(self.plan)
            self.plan = []
            self.table.setRowCount(0)
            self.count_label.setText("Файлов: 0")
            self.statusBar().showMessage(f"Переименование завершено. Журнал: {log.name}")
            QMessageBox.information(self, "Готово", f"Файлы переименованы.\nЖурнал операции сохранён в папке .FileShuffleRenamer.")
        except RenameError as e:
            QMessageBox.critical(self, "Ошибка переименования", str(e))

    def undo(self):
        if not self.folder:
            QMessageBox.information(self, "Папка не выбрана", "Выберите папку, в которой выполнялось переименование.")
            return
        answer = QMessageBox.question(self, "Подтверждение", "Отменить последнее переименование?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            result = undo_last(self.folder)
            self.statusBar().showMessage(result)
            QMessageBox.information(self, "Отмена выполнена", result)
            self.load_files()
        except (RenameError, OSError, ValueError) as e:
            QMessageBox.critical(self, "Не удалось отменить", str(e))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("File Shuffle Renamer")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
