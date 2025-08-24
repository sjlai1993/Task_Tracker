# edit_tab.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTableWidget, QTableWidgetItem, QDateEdit,
                             QGroupBox, QGridLayout, QCalendarWidget, QHeaderView,
                             QMessageBox)
from PySide6.QtCore import Qt, QSize, QDate
from PySide6.QtGui import QColor, QTextCharFormat, QTextDocument
from datetime import datetime, time, timedelta

class EditTab(QWidget):
    COLUMN_HEADERS = ["Start Time", "End Time", "Project Code", "Description", 
                      "Categories", "Software", "Time Spent (h)"]

    def __init__(self, parent, db, config):
        super().__init__()
        self.parent_window = parent
        self.db = db
        self.config = config
        self.view_date = datetime.now().date()
        self.is_updating = False

        self.holiday_format = QTextCharFormat()
        self.holiday_format.setForeground(QColor("red"))
        
        self.init_ui()
        self.update_task_view()

    def init_ui(self):
        layout = QVBoxLayout(self)
        nav_group = QGroupBox("Date Navigation")
        nav_layout = QGridLayout(nav_group)
        prev_button = QPushButton("<")
        prev_button.clicked.connect(self._go_to_previous_day)
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDisplayFormat("dd/MM/yyyy, dddd")
        self.date_picker.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_picker.setMaximumDate(QDate.currentDate())
        calendar = self.date_picker.calendarWidget()
        calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.ISOWeekNumbers)
        self.date_picker.dateChanged.connect(self._on_date_picker_changed)
        self.next_button = QPushButton(">")
        self.next_button.clicked.connect(self._go_to_next_day)
        nav_layout.addWidget(prev_button, 0, 0)
        nav_layout.addWidget(self.date_picker, 0, 1)
        nav_layout.addWidget(self.next_button, 0, 2)
        nav_layout.setColumnStretch(1, 1)
        layout.addWidget(nav_group)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(self.COLUMN_HEADERS)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        delete_button = QPushButton("Delete Selected Task")
        delete_button.clicked.connect(self._delete_selected_task)
        button_layout.addWidget(delete_button)
        save_button = QPushButton("Save Changes")
        save_button.clicked.connect(self._save_changes)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)

    def _update_calendar_holidays(self):
        calendar = self.date_picker.calendarWidget()
        calendar.setDateTextFormat(QDate(), QTextCharFormat())
        for date_str in self.config.get("holidays", []):
            try:
                date = QDate.fromString(date_str, "yyyy-MM-dd")
                if date.isValid():
                    calendar.setDateTextFormat(date, self.holiday_format)
            except Exception as e:
                print(f"Error parsing holiday date '{date_str}': {e}")

    def _on_date_picker_changed(self, new_qdate):
        self.view_date = new_qdate.toPython()
        self.update_task_view()

    def _go_to_previous_day(self):
        self.view_date -= timedelta(days=1)
        self.update_task_view()

    def _go_to_next_day(self):
        self.view_date += timedelta(days=1)
        self.update_task_view()

    def update_task_view(self):
        self.is_updating = True
        self.date_picker.blockSignals(True)
        self.date_picker.setDate(QDate(self.view_date))
        self.date_picker.blockSignals(False)
        self.next_button.setEnabled(self.view_date < datetime.now().date())
        self._update_calendar_holidays()
        
        self.table.setRowCount(0)
        date_str = self.view_date.strftime("%Y-%m-%d")
        
        tasks = self.db.get_tasks_for_date(date_str)
        self.table.setRowCount(len(tasks))
        
        for row, task_data in enumerate(tasks):
            task_id, _, start_str, end_str, proj, desc_html, cats, soft = task_data
            
            doc = QTextDocument()
            doc.setHtml(desc_html)
            
            items = [start_str, end_str, proj, doc.toPlainText(), cats, soft]
            
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                self.table.setItem(row, col, item)
            
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, task_id)

            duration_item = QTableWidgetItem()
            duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, self.COLUMN_HEADERS.index("Time Spent (h)"), duration_item)
            self._calculate_and_set_duration(row)
        
        self.table.resizeColumnsToContents()
        self.is_updating = False

    def _on_cell_changed(self, row, column):
        if self.is_updating:
            return
        
        start_col = self.COLUMN_HEADERS.index("Start Time")
        end_col = self.COLUMN_HEADERS.index("End Time")
        if column in [start_col, end_col]:
            self._calculate_and_set_duration(row)
    
    def _calculate_and_set_duration(self, row):
        self.is_updating = True
        
        start_item = self.table.item(row, self.COLUMN_HEADERS.index("Start Time"))
        end_item = self.table.item(row, self.COLUMN_HEADERS.index("End Time"))
        duration_item = self.table.item(row, self.COLUMN_HEADERS.index("Time Spent (h)"))
        
        if start_item and end_item and duration_item:
            try:
                start_t = time.fromisoformat(start_item.text())
                end_t = time.fromisoformat(end_item.text())
                start_dt = datetime.combine(datetime.min, start_t)
                end_dt = datetime.combine(datetime.min, end_t)
                duration_hours = (end_dt - start_dt).total_seconds() / 3600
                if duration_hours < 0:
                    duration_hours = 0
                duration_item.setText(f"{duration_hours:.2f}")
            except ValueError:
                duration_item.setText("Invalid")
        
        self.is_updating = False

    def _delete_selected_task(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a task to delete.")
            return

        task_id = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        project_code = self.table.item(current_row, 2).text()
        
        reply = QMessageBox.question(self, "Confirm Delete", 
            f"Are you sure you want to delete the task for project '{project_code}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_task_by_id(task_id)
            self.table.removeRow(current_row)
            self.parent_window.general_tab.update_task_view()
            QMessageBox.information(self, "Success", "Task deleted successfully.")

    def _save_changes(self):
        rows = self.table.rowCount()
        for row in range(rows):
            task_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            
            try:
                time.fromisoformat(self.table.item(row, 0).text())
                time.fromisoformat(self.table.item(row, 1).text())
            except (ValueError, AttributeError):
                QMessageBox.critical(self, "Save Error", f"Invalid time format in row {row+1}. Please use HH:MM:SS.")
                return

            # =====================================================================
            # === MODIFIED SECTION START (Format description as HTML on save) ===
            # =====================================================================
            plain_text_desc = self.table.item(row, 3).text()
            # Convert plain text newlines to HTML line breaks for consistency
            html_desc = plain_text_desc.replace('\n', '<br>')
            
            task_data = {
                'start_time': self.table.item(row, 0).text(),
                'end_time': self.table.item(row, 1).text(),
                'project_code': self.table.item(row, 2).text(),
                'description': html_desc,
                'categories': self.table.item(row, 4).text(),
                'software': self.table.item(row, 5).text(),
            }
            # =====================================================================
            # === MODIFIED SECTION END ===
            # =====================================================================
            self.db.update_task_by_id(task_id, task_data)
        
        self.parent_window.general_tab.update_task_view()
        QMessageBox.information(self, "Success", "All changes saved successfully.")