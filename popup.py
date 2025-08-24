# popup.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QDateEdit, QTimeEdit, QPushButton, QCheckBox, QGroupBox,
                             QTextEdit, QScrollArea, QWidget, QMessageBox, QGridLayout,
                             QSystemTrayIcon, QCalendarWidget)
from PySide6.QtCore import QDate, QTime, Qt, QTimer
from PySide6.QtGui import QFont, QTextCharFormat, QKeySequence, QColor
from datetime import datetime, timedelta, time
from database import Database
import json

class Popup(QDialog):
    def __init__(self, db, previous_task, config, parent=None, is_manual_trigger=False):
        super().__init__(parent)
        self.db = db
        self.previous_task = previous_task
        self.config = config # Use the passed-in config object
        self.original_title = "Log Your Task"
        self.setWindowTitle(self.original_title)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.help_window = None
        
        self.holiday_format = QTextCharFormat()
        self.holiday_format.setForeground(QColor("red"))
        
        self.init_ui()
        self.set_initial_values()
        
        if not is_manual_trigger:
            autoclose_minutes = self.config.get("popup_autoclose_minutes", 2)
            if autoclose_minutes > 0:
                self.time_remaining_seconds = float(autoclose_minutes * 60)
                self.countdown_timer = QTimer(self)
                self.countdown_timer.timeout.connect(self._update_countdown)
                self.countdown_timer.start(100)
                self._update_countdown()

    def show_help_message(self):
        if self.help_window and self.help_window.isVisible():
            self.help_window.activateWindow()
            return
        description_data = self.config.get('side_description', '')
        message_text = "\n".join(description_data) if isinstance(description_data, list) else description_data
        self.help_window = QDialog(self)
        self.help_window.setWindowTitle("Additional Codes")
        self.help_window.setWindowFlags(self.help_window.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.help_window.setMinimumWidth(300)
        layout = QVBoxLayout(self.help_window)
        label = QLabel(message_text)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(label)
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.help_window.close)
        layout.addWidget(ok_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.help_window.show()

    def _update_countdown(self):
        if self.time_remaining_seconds <= 0:
            self.countdown_timer.stop()
            self.reject()
            return
        self.setWindowTitle(f"{self.original_title} ({self.time_remaining_seconds:.1f}s remaining)")
        self.time_remaining_seconds -= 0.1

    def _create_scrollable_checkbox_group(self, title, items):
        group_box = QGroupBox(title)
        group_box_layout = QVBoxLayout(group_box)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_content_widget = QWidget()
        scroll_content_layout = QVBoxLayout(scroll_content_widget)
        scroll_content_layout.setContentsMargins(5, 5, 5, 5)
        scroll_content_layout.setSpacing(5)
        checkbox_list = []
        for item in items:
            checkbox = QCheckBox(item)
            checkbox_list.append(checkbox)
            scroll_content_layout.addWidget(checkbox)
        scroll_content_layout.addStretch()
        scroll_area.setWidget(scroll_content_widget)
        if len(items) > 3:
            temp_checkbox = QCheckBox("Test")
            height = temp_checkbox.sizeHint().height() * 4.2
            scroll_area.setMaximumHeight(int(height))
        group_box_layout.addWidget(scroll_area)
        return group_box, checkbox_list

    def _format_bold(self):
        cursor = self.description_input.textCursor()
        fmt = cursor.charFormat()
        is_bold = fmt.fontWeight() == QFont.Weight.Bold
        fmt.setFontWeight(QFont.Weight.Normal if is_bold else QFont.Weight.Bold)
        cursor.mergeCharFormat(fmt)
        self.description_input.setFocus()

    def _format_italic(self):
        cursor = self.description_input.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        cursor.mergeCharFormat(fmt)
        self.description_input.setFocus()

    def _format_underline(self):
        cursor = self.description_input.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        cursor.mergeCharFormat(fmt)
        self.description_input.setFocus()
    
    def _update_calendar_holidays(self):
        calendar = self.date_edit.calendarWidget()
        calendar.setDateTextFormat(QDate(), QTextCharFormat())
        for date_str in self.config.get("holidays", []):
            try:
                date = QDate.fromString(date_str, "yyyy-MM-dd")
                if date.isValid():
                    calendar.setDateTextFormat(date, self.holiday_format)
            except Exception as e:
                print(f"Error parsing holiday date '{date_str}': {e}")
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        datetime_group = QGroupBox("Date && Time")
        grid_layout = QGridLayout(datetime_group)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        calendar = self.date_edit.calendarWidget()
        calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.ISOWeekNumbers)
        grid_layout.addWidget(QLabel("Date:"), 0, 0)
        grid_layout.addWidget(self.date_edit, 0, 1, 1, 3)
        self.start_time_edit = QTimeEdit()
        self.end_time_edit = QTimeEdit()
        grid_layout.addWidget(QLabel("Start:"), 1, 0)
        grid_layout.addWidget(self.start_time_edit, 1, 1)
        grid_layout.addWidget(QLabel("End:"), 1, 2)
        grid_layout.addWidget(self.end_time_edit, 1, 3)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(3, 1)
        main_layout.addWidget(datetime_group)
        main_layout.addWidget(QLabel("Project Code:"))
        self.project_code_input = QLineEdit()
        main_layout.addWidget(self.project_code_input)
        main_layout.addWidget(QLabel("Description:"))
        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(100)
        main_layout.addWidget(self.description_input)
        self.same_as_prev_checkbox = QCheckBox("Same as previous task")
        self.same_as_prev_checkbox.stateChanged.connect(self._on_copy_previous_task_toggled)
        main_layout.addWidget(self.same_as_prev_checkbox)
        checkbox_groups_layout = QHBoxLayout()
        self.categories_group, self.category_checkboxes = self._create_scrollable_checkbox_group(
            "Categories", self.config['project_categories']
        )
        self.software_group, self.software_checkboxes = self._create_scrollable_checkbox_group(
            "Software Used", self.config['software_used']
        )
        fixed_group_width = 170
        self.categories_group.setFixedWidth(fixed_group_width)
        self.software_group.setFixedWidth(fixed_group_width)
        checkbox_groups_layout.addWidget(self.categories_group)
        checkbox_groups_layout.addWidget(self.software_group)
        main_layout.addLayout(checkbox_groups_layout)
        bottom_button_layout = QHBoxLayout()
        self.help_button = QPushButton("Additional Codes")
        self.help_button.setToolTip("Show additional project and claimable codes")
        self.help_button.clicked.connect(self.show_help_message)
        self.help_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        bottom_button_layout.addWidget(self.help_button)
        hint_label = QLabel("<i>Ctrl+Enter to save.</i>")
        bottom_button_layout.addWidget(hint_label)
        bottom_button_layout.addStretch()
        self.skip_button = QPushButton("Skip")
        self.skip_button.setToolTip("Close the popup without saving")
        self.skip_button.clicked.connect(self.skip_task)
        self.skip_button.setAutoDefault(False)
        bottom_button_layout.addWidget(self.skip_button)
        self.save_button = QPushButton("Save Task")
        self.save_button.setToolTip("Save the current task (Ctrl+Enter)")
        self.save_button.clicked.connect(self.save_task)
        self.save_button.setEnabled(False)
        self.save_button.setAutoDefault(False)
        bottom_button_layout.addWidget(self.save_button)
        main_layout.addLayout(bottom_button_layout)
        self.project_code_input.textChanged.connect(self._update_save_button_state)
        self.description_input.textChanged.connect(self._update_save_button_state)
        self.setFixedSize(self.sizeHint())
        self.project_code_input.setFocus()
        self._update_calendar_holidays()

    def _on_copy_previous_task_toggled(self, state):
        is_checked = (state == Qt.CheckState.Checked.value)
        widgets_to_manage = [
            self.project_code_input, self.description_input,
            self.categories_group, self.software_group,
            self.help_button, self.skip_button
        ]
        if is_checked and self.previous_task:
            self.project_code_input.setText(self.previous_task[4])
            self.description_input.setHtml(self.previous_task[5])
            prev_cats = self.previous_task[6].split(',') if self.previous_task[6] else []
            for cb in self.category_checkboxes: cb.setChecked(cb.text() in prev_cats)
            prev_sw = self.previous_task[7].split(',') if self.previous_task[7] else []
            for cb in self.software_checkboxes: cb.setChecked(cb.text() in prev_sw)
            for widget in widgets_to_manage: widget.setEnabled(False)
            self.save_button.setEnabled(True)
        else:
            self.project_code_input.clear()
            self.description_input.clear()
            for cb in self.category_checkboxes: cb.setChecked(False)
            for cb in self.software_checkboxes: cb.setChecked(False)
            for widget in widgets_to_manage: widget.setEnabled(True)
            self._update_save_button_state()

    def keyPressEvent(self, event):
        if self.description_input.hasFocus():
            if event.matches(QKeySequence.StandardKey.Bold): self._format_bold(); return
            if event.matches(QKeySequence.StandardKey.Italic): self._format_italic(); return
            if event.matches(QKeySequence.StandardKey.Underline): self._format_underline(); return
        is_ctrl_enter = (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and
                         event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if is_ctrl_enter and self.save_button.isEnabled():
            self.save_task()
            return
        super().keyPressEvent(event)

    def _show_notification(self, title, message):
        if self.parent() and hasattr(self.parent(), 'tray_icon'):
            self.parent().tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.NoIcon, 5000)

    def save_task(self):
        if hasattr(self, 'countdown_timer'): self.countdown_timer.stop()
        selected_date = self.date_edit.date().toPython()
        date_str = selected_date.strftime("%Y-%m-%d")
        day_rules = {}
        work_times_row = self.db.get_work_times_for_date(date_str)
        if work_times_row:
            # =====================================================================
            # === MODIFIED SECTION START (Corrected DB indices) ===
            # =====================================================================
            # Indices were off by one, causing the bug. Corrected to 7 and 8.
            day_rules = {
                'lower': work_times_row[2], 'upper': work_times_row[3],
                'hours': work_times_row[4], 'lunch_s': work_times_row[5],
                'lunch_e': work_times_row[6], 
                'work_days': work_times_row[7].split(','),
                'holidays': work_times_row[8].split(',')
            }
            # =====================================================================
            # === MODIFIED SECTION END ===
            # =====================================================================
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
        
        day_name = selected_date.strftime('%A')
        if date_str in day_rules['holidays'] or day_name not in day_rules['work_days']:
            self._show_notification("Invalid Time", f"Cannot log tasks on a non-working day ({day_name}).")
            return
            
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
        work_start_dt = datetime.combine(selected_date, work_start_t)
        lunch_s = time.fromisoformat(day_rules['lunch_s'])
        lunch_e = time.fromisoformat(day_rules['lunch_e'])
        lunch_dur = datetime.combine(selected_date, lunch_e) - datetime.combine(selected_date, lunch_s)
        work_dur = timedelta(hours=day_rules['hours'])
        work_end_dt = work_start_dt + work_dur + lunch_dur
        lunch_start_dt = datetime.combine(selected_date, lunch_s)
        lunch_end_dt = datetime.combine(selected_date, lunch_e)
        task_start_dt = datetime.combine(selected_date, self.start_time_edit.time().toPython())
        task_end_dt = datetime.combine(selected_date, self.end_time_edit.time().toPython())
        if task_end_dt <= work_start_dt or task_start_dt >= work_end_dt:
            self._show_notification("Invalid Time", "Task is completely outside of working hours.")
            return
        if task_start_dt >= lunch_start_dt and task_end_dt <= lunch_end_dt:
            self._show_notification("Invalid Time", "Cannot log tasks during lunch hour.")
            return
        preliminary_slots = []
        task_start_dt = max(task_start_dt, work_start_dt)
        task_end_dt = min(task_end_dt, work_end_dt)
        if task_start_dt < lunch_start_dt and task_end_dt > lunch_end_dt:
            preliminary_slots.append((task_start_dt, lunch_start_dt))
            preliminary_slots.append((lunch_end_dt, task_end_dt))
        else:
            if task_start_dt >= lunch_start_dt and task_start_dt < lunch_end_dt: task_start_dt = lunch_end_dt
            if task_end_dt > lunch_start_dt and task_end_dt <= lunch_end_dt: task_end_dt = lunch_start_dt
            if task_start_dt < task_end_dt:
                preliminary_slots.append((task_start_dt, task_end_dt))
        if not preliminary_slots:
            self._show_notification("Invalid Time", "Task has no duration after adjusting for work/lunch hours.")
            return
        existing_tasks = self.db.get_tasks_for_date(date_str)
        project_code = self.project_code_input.text()
        description = self.description_input.toHtml()
        categories = ",".join([cb.text() for cb in self.category_checkboxes if cb.isChecked()])
        software = ",".join([cb.text() for cb in self.software_checkboxes if cb.isChecked()])
        tasks_added = 0
        for slot_start, slot_end in preliminary_slots:
            candidate_start = slot_start
            for task_row in existing_tasks:
                existing_start = datetime.combine(selected_date, datetime.strptime(task_row[2], '%H:%M:%S').time())
                existing_end = datetime.combine(selected_date, datetime.strptime(task_row[3], '%H:%M:%S').time())
                if candidate_start < existing_start:
                    sub_slot_end = min(slot_end, existing_start)
                    if candidate_start < sub_slot_end:
                        self.db.add_task(date_str, candidate_start.strftime("%H:%M:%S"), sub_slot_end.strftime("%H:%M:%S"), project_code, description, categories, software)
                        tasks_added += 1
                candidate_start = max(candidate_start, existing_end)
                if candidate_start >= slot_end: break
            if candidate_start < slot_end:
                self.db.add_task(date_str, candidate_start.strftime("%H:%M:%S"), slot_end.strftime("%H:%M:%S"), project_code, description, categories, software)
                tasks_added += 1
        if tasks_added > 0:
            self.accept()
        else:
            self._show_notification("Time Blocked", "The selected time is already fully occupied by other tasks.")
            
    def _update_save_button_state(self):
        project_code_ok = bool(self.project_code_input.text().strip())
        description_ok = bool(self.description_input.toPlainText().strip())
        self.save_button.setEnabled(project_code_ok and description_ok)

    def set_initial_values(self):
        self.date_edit.setDate(QDate.currentDate())
        self.end_time_edit.setTime(QTime.currentTime())

    def skip_task(self):
        if hasattr(self, 'countdown_timer'): self.countdown_timer.stop()
        self.reject()