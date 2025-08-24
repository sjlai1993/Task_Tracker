# general_tab.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QListWidget, QListWidgetItem, QDateEdit,
                             QGroupBox, QGridLayout, QCalendarWidget, QStyle,
                             QApplication, QMessageBox, QSystemTrayIcon)
from PySide6.QtCore import Qt, QSize, QDate
from PySide6.QtGui import QColor, QTextCharFormat, QTextDocument
from datetime import datetime, time, timedelta

class GeneralTab(QWidget):
    def __init__(self, parent, db, config):
        super().__init__()
        self.parent_window = parent
        self.db = db
        self.config = config
        self.view_date = datetime.now().date()
        
        self.holiday_format = QTextCharFormat()
        self.holiday_format.setForeground(QColor("red"))
        
        self.init_ui()
        self._update_calendar_holidays()

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
        self.task_list_widget = QListWidget()
        self.task_list_widget.setIconSize(QSize(0, 0))
        self.task_list_widget.setWordWrap(True) # Important for resizing
        layout.addWidget(self.task_list_widget)
        manual_popup_button = QPushButton("Log a Task")
        manual_popup_button.clicked.connect(self.parent_window.manual_popup)
        layout.addWidget(manual_popup_button)

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
        """Handle when the user selects a new date from the calendar."""
        self.view_date = new_qdate.toPython()
        self.update_task_view()

    def _go_to_previous_day(self):
        self.view_date -= timedelta(days=1)
        self.update_task_view()

    def _go_to_next_day(self):
        self.view_date += timedelta(days=1)
        self.update_task_view()

    def _create_item_widget(self, rich_text, task, is_unrecorded, is_day_off):
        """Creates the custom widget for each list item with text and buttons."""
        item_widget = QWidget()
        main_layout = QHBoxLayout(item_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        label = QLabel(rich_text)
        label.setWordWrap(True)
        # MODIFIED SECTION: This is the key change to align the label's content.
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(label, 1) # Give label stretch factor of 1

        # --- Create icon buttons ---
        style = self.style()
        copy_btn = QPushButton(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView), "")
        edit_btn = QPushButton(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "")
        delete_btn = QPushButton(style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton), "")
        
        copy_btn.setToolTip("Copy task description")
        edit_btn.setToolTip("Edit task (Not implemented)")
        delete_btn.setToolTip("Delete task")

        buttons = [copy_btn, edit_btn, delete_btn]
        for btn in buttons:
            btn.setFixedSize(24, 24)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # --- Connect button signals ---
        if not is_unrecorded:
            copy_btn.clicked.connect(lambda: self._copy_task_desc(task[5]))
            delete_btn.clicked.connect(lambda: self._delete_task(task[0], task[4]))
        
        # --- Set button enabled state ---
        copy_btn.setEnabled(not is_unrecorded and not is_day_off)
        edit_btn.setEnabled(False) # Edit functionality is complex and not fully specified here.
        delete_btn.setEnabled(not is_unrecorded and not is_day_off)
        
        # --- Layout for buttons ---
        right_panel_layout = QVBoxLayout()
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        
        button_row_layout = QHBoxLayout()
        button_row_layout.setContentsMargins(0, 0, 0, 0)
        button_row_layout.setSpacing(2)
        button_row_layout.addWidget(copy_btn)
        button_row_layout.addWidget(edit_btn)
        button_row_layout.addWidget(delete_btn)
        
        right_panel_layout.addLayout(button_row_layout)
        right_panel_layout.addStretch()

        main_layout.addLayout(right_panel_layout)
        return item_widget

    def _add_recorded_task_item(self, task, is_day_off):
        """Adds a QListWidgetItem for a recorded task."""
        start_dt = datetime.combine(self.view_date, time.fromisoformat(task[2]))
        end_dt = datetime.combine(self.view_date, time.fromisoformat(task[3]))
        project_code = task[4]
        description_html = task[5]
        
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        start_str = start_dt.strftime("%H:%M")
        end_str = end_dt.strftime("%H:%M")
        rich_text = (f"<b>{start_str} - {end_str} ({duration_hours:.2f}h)</b>"
                     f" | <b>{project_code}</b> | {description_html}")
        
        widget = self._create_item_widget(rich_text, task, is_unrecorded=False, is_day_off=is_day_off)
        
        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())
        self.task_list_widget.addItem(item)
        self.task_list_widget.setItemWidget(item, widget)

    def _add_unrecorded_task_item(self, start_dt, end_dt, is_day_off):
        """Adds a QListWidgetItem for an unrecorded time slot."""
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        start_str = start_dt.strftime("%H:%M")
        end_str = end_dt.strftime("%H:%M")
        rich_text = (f"<b>{start_str} - {end_str} ({duration_hours:.2f}h)</b>"
                     f" | <b>---</b> | <i>Unrecorded</i>")
                     
        widget = self._create_item_widget(rich_text, task=None, is_unrecorded=True, is_day_off=is_day_off)

        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())
        self.task_list_widget.addItem(item)
        self.task_list_widget.setItemWidget(item, widget)

    def update_task_view(self):
        self.date_picker.blockSignals(True)
        self.date_picker.setDate(QDate(self.view_date))
        self.date_picker.blockSignals(False)
        self.next_button.setEnabled(self.view_date < datetime.now().date())
        self._update_calendar_holidays()
        self.task_list_widget.clear()

        date_str = self.view_date.strftime("%Y-%m-%d")
        day_name = self.view_date.strftime('%A')
        day_rules = {}
        is_day_off = False

        work_times_row = self.db.get_work_times_for_date(date_str)
        if work_times_row:
            day_rules = {
                'lower': work_times_row[2], 'upper': work_times_row[3],
                'hours': work_times_row[4], 'lunch_s': work_times_row[5],
                'lunch_e': work_times_row[6], 'work_days': work_times_row[7].split(','),
                'holidays': work_times_row[8].split(',')
            }
        else:
            day_rules = {
                'lower': self.config['work_start_time_flexible']['lower'],
                'upper': self.config['work_start_time_flexible']['upper'],
                'hours': self.config['daily_working_hours'],
                'lunch_s': self.config['lunch_hour']['start'],
                'lunch_e': self.config['lunch_hour']['end'],
                'work_days': self.config['working_days'],
                'holidays': self.config['holidays']
            }

        if date_str in day_rules['holidays']:
            self.task_list_widget.addItem("Public Holiday"); is_day_off = True
        if day_name not in day_rules['work_days']:
            self.task_list_widget.addItem(f"Not a working day ({day_name})"); is_day_off = True
        if is_day_off: return

        tasks = self.db.get_tasks_for_date(date_str)
        work_start_t = None
        if work_times_row:
            work_start_t = time.fromisoformat(work_times_row[1])
        elif tasks:
            earliest_task_t = time.fromisoformat(tasks[0][2])
            lower_bound = time.fromisoformat(day_rules['lower'])
            upper_bound = time.fromisoformat(day_rules['upper'])
            work_start_t = earliest_task_t if lower_bound <= earliest_task_t <= upper_bound else upper_bound
        else:
            work_start_t = time.fromisoformat(day_rules['upper'])

        work_start_dt = datetime.combine(self.view_date, work_start_t)
        lunch_s = time.fromisoformat(day_rules['lunch_s'])
        lunch_e = time.fromisoformat(day_rules['lunch_e'])
        lunch_dur = datetime.combine(self.view_date, lunch_e) - datetime.combine(self.view_date, lunch_s)
        work_dur = timedelta(hours=day_rules['hours'])
        work_end_dt = work_start_dt + work_dur + lunch_dur
        lunch_start_dt = datetime.combine(self.view_date, lunch_s)
        lunch_end_dt = datetime.combine(self.view_date, lunch_e)

        if not tasks:
            if work_start_dt < work_end_dt:
                self._add_unrecorded_slots(work_start_dt, work_end_dt, lunch_start_dt, lunch_end_dt, is_day_off)
            else:
                 self.task_list_widget.addItem("No tasks saved for this day.")
            return

        timeline_cursor = work_start_dt
        for task in tasks:
            task_start_dt = datetime.combine(self.view_date, time.fromisoformat(task[2]))
            if timeline_cursor < task_start_dt:
                self._add_unrecorded_slots(timeline_cursor, task_start_dt, lunch_start_dt, lunch_end_dt, is_day_off)
            
            self._add_recorded_task_item(task, is_day_off)
            
            task_end_dt = datetime.combine(self.view_date, time.fromisoformat(task[3]))
            timeline_cursor = max(timeline_cursor, task_end_dt)

        if timeline_cursor < work_end_dt:
            self._add_unrecorded_slots(timeline_cursor, work_end_dt, lunch_start_dt, lunch_end_dt, is_day_off)

    def _add_unrecorded_slots(self, start_dt, end_dt, lunch_start_dt, lunch_end_dt, is_day_off):
        pre_lunch_end = min(end_dt, lunch_start_dt)
        if start_dt < pre_lunch_end:
            self._add_unrecorded_task_item(start_dt, pre_lunch_end, is_day_off)
        
        post_lunch_start = max(start_dt, lunch_end_dt)
        if post_lunch_start < end_dt:
            self._add_unrecorded_task_item(post_lunch_start, end_dt, is_day_off)

    def _copy_task_desc(self, html_description):
        """Copies the plain text of a task's description to the clipboard."""
        doc = QTextDocument()
        doc.setHtml(html_description)
        plain_text = doc.toPlainText()
        QApplication.clipboard().setText(plain_text)
        self.parent_window.tray_icon.showMessage(
            "Copied", "Task description copied to clipboard.",
            QSystemTrayIcon.MessageIcon.NoIcon, 2000
        )

    def _delete_task(self, task_id, project_code):
        """Deletes a task after confirmation."""
        reply = QMessageBox.question(self, "Confirm Delete",
            f"Are you sure you want to delete the task for project '{project_code}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            # Assuming db.delete_task_by_id exists from edit_tab.py context
            if hasattr(self.db, 'delete_task_by_id'):
                self.db.delete_task_by_id(task_id)
                self.update_task_view()
                # Safely try to update edit_tab if it exists
                if hasattr(self.parent_window, 'edit_tab'):
                    try:
                        self.parent_window.edit_tab.update_task_view()
                    except Exception as e:
                        print(f"Could not refresh edit tab: {e}")
            else:
                QMessageBox.critical(self, "Error", "Database function 'delete_task_by_id' not found.")