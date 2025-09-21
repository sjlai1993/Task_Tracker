# popup.py

import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QDateEdit, QTimeEdit, QPushButton, QCheckBox, QGroupBox,
                             QTextEdit, QScrollArea, QWidget, QMessageBox, QGridLayout,
                             QSystemTrayIcon, QCalendarWidget, QApplication, QCompleter)
from PySide6.QtCore import QDate, QTime, Qt, QTimer, QEvent
from PySide6.QtGui import (QFont, QTextCharFormat, QKeySequence, QColor, QKeyEvent,
                         QTextDocument)
from datetime import datetime, timedelta, time
from database import Database

class Popup(QDialog):
    def __init__(self, db, previous_task, config, parent=None, is_manual_trigger=False):
        super().__init__(parent)
        self.db = db
        self.previous_task = previous_task
        self.config = config
        self.original_title = "Log Your Task"
        self.countdown_stopped = False
        
        self.setWindowTitle(self.original_title)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.help_window = None
        
        self.holiday_format = QTextCharFormat()
        self.holiday_format.setForeground(QColor("red"))
        
        self.pre_full_day_start_time = None
        self.pre_full_day_end_time = None
        
        self.init_ui()
        self.set_initial_values()

        interactive_widget_types = (
            QLineEdit, QDateEdit, QTimeEdit, 
            QCheckBox, QPushButton
        )
        
        all_children = self.findChildren(QWidget)
        
        for widget in all_children:
            if isinstance(widget, interactive_widget_types):
                widget.installEventFilter(self)
        
        self.description_input.viewport().installEventFilter(self)
        self.categories_group.findChild(QScrollArea).viewport().installEventFilter(self)

        self.installEventFilter(self)

        if not is_manual_trigger:
            autoclose_minutes = self.config.get("popup_autoclose_minutes", 2)
            if autoclose_minutes > 0:
                self.time_remaining_seconds = float(autoclose_minutes * 60)
                self.countdown_timer = QTimer(self)
                self.countdown_timer.timeout.connect(self._update_countdown)
                self.countdown_timer.start(100)
                self._update_countdown()

    def showEvent(self, event):
        """Positions the popup at the bottom-right corner of the screen when shown."""
        super().showEvent(event)
        
        if not hasattr(self, '_initial_pos_set'):
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry() 
                padding = 20
                x = screen_geometry.right() - self.width() - padding
                y = screen_geometry.bottom() - self.height() - padding
                self.move(x, y)
                self._initial_pos_set = True

    def exec(self):
        """
        Overrides the default exec() to ensure the window is activated and
        brought to the front before being shown as a modal dialog.
        """
        self.activateWindow()
        self.raise_()
        return super().exec()

    def _stop_countdown(self):
        if not self.countdown_stopped and hasattr(self, 'countdown_timer') and self.countdown_timer.isActive():
            self.countdown_timer.stop()
            self.setWindowTitle(self.original_title)
            self.countdown_stopped = True

    def eventFilter(self, watched_object, event):
        if not self.countdown_stopped and hasattr(self, 'countdown_timer') and self.countdown_timer.isActive():
            if event.type() in [QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress]:
                self._stop_countdown()
        
        if event.type() == QEvent.Type.KeyPress:
            if self.description_input.hasFocus():
                if event.matches(QKeySequence.StandardKey.Bold):
                    self._format_bold()
                    return True
                if event.matches(QKeySequence.StandardKey.Italic):
                    self._format_italic()
                    return True
                if event.matches(QKeySequence.StandardKey.Underline):
                    self._format_underline()
                    return True

            is_ctrl_enter = (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and
                             event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            if is_ctrl_enter and self.save_button.isEnabled():
                self.save_task()
                return True

        return super().eventFilter(watched_object, event)
    
    # =====================================================================
    # === MODIFIED SECTION START (Disable closing with Esc key) ===
    # =====================================================================
    def keyPressEvent(self, event: QKeyEvent):
        """
        Overrides the default key press event handler to prevent the Escape
        key from closing the dialog. The "Skip" button should be used instead.
        """
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
        else:
            super().keyPressEvent(event)
    # =====================================================================
    # === MODIFIED SECTION END ===
    # =====================================================================
    
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
            if hasattr(self, 'countdown_timer'):
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
        self.date_edit.dateChanged.connect(self._on_date_changed)

        self.full_day_checkbox = QCheckBox("Full Day")
        self.full_day_checkbox.stateChanged.connect(self._on_full_day_toggled)

        grid_layout.addWidget(QLabel("Date:"), 0, 0)
        grid_layout.addWidget(self.date_edit, 0, 1)
        grid_layout.addWidget(self.full_day_checkbox, 0, 2, 1, 2, Qt.AlignmentFlag.AlignLeft)

        self.start_time_edit = QTimeEdit()
        self.end_time_edit = QTimeEdit()
        grid_layout.addWidget(QLabel("Start:"), 1, 0)
        grid_layout.addWidget(self.start_time_edit, 1, 1)
        grid_layout.addWidget(QLabel("End:"), 1, 2)
        grid_layout.addWidget(self.end_time_edit, 1, 3)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(3, 1)
        main_layout.addWidget(datetime_group)

        # Main input area layout (Project/Categories on left, Description on right)
        input_area_layout = QHBoxLayout()

        # Left side: Project Code and Categories
        left_input_layout = QVBoxLayout()
        left_input_layout.addWidget(QLabel("Project Code"))
        self.project_code_input = QLineEdit()
        project_codes = self.db.get_unique_project_codes()
        self.project_completer = QCompleter(project_codes, self)
        self.project_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.project_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.project_code_input.setCompleter(self.project_completer)
        left_input_layout.addWidget(self.project_code_input)

        self.categories_group, self.category_checkboxes = self._create_scrollable_checkbox_group("Categories", self.config['project_categories'])
        left_input_layout.addWidget(self.categories_group)
        
        # Right side: Task Description
        right_input_layout = QVBoxLayout()
        right_input_layout.addWidget(QLabel("Task Description"))
        self.description_input = QTextEdit()
        self.description_input.setTabChangesFocus(True)
        right_input_layout.addWidget(self.description_input)

        input_area_layout.addLayout(left_input_layout, 0)
        input_area_layout.addLayout(right_input_layout, 1)

        main_layout.addLayout(input_area_layout)

        self.same_as_prev_checkbox = QCheckBox("Same as previous task")
        self.same_as_prev_checkbox.stateChanged.connect(self._on_copy_previous_task_toggled)
        main_layout.addWidget(self.same_as_prev_checkbox)

        for checkbox in self.category_checkboxes:
            if checkbox.text() == "QA83":
                checkbox.setChecked(True)
                break

        bottom_button_layout = QHBoxLayout()
        self.help_button = QPushButton("Additional Codes")
        self.help_button.setToolTip("Show additional project and claimable codes")
        self.help_button.clicked.connect(self.show_help_message)
        self.help_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        bottom_button_layout.addWidget(self.help_button)
        bottom_button_layout.addStretch()
        self.skip_button = QPushButton("Skip")
        self.skip_button.setToolTip("Close the popup without saving")
        self.skip_button.clicked.connect(self.skip_task)
        self.skip_button.setAutoDefault(False)
        #self.skip_button.setStyleSheet("color: red;")
        bottom_button_layout.addWidget(self.skip_button)
        self.save_button = QPushButton("Save Task (Ctrl+⏎)")
        self.save_button.setToolTip("Save the current task (Ctrl+⏎)")
        self.save_button.clicked.connect(self.save_task)
        self.save_button.setEnabled(False)
        self.save_button.setDefault(True)
        bottom_button_layout.addWidget(self.save_button)
        main_layout.addLayout(bottom_button_layout)
        self.project_code_input.textChanged.connect(self._update_save_button_state)
        self.description_input.textChanged.connect(self._update_save_button_state)

        # Calculate and set a reduced width for the window.
        hint = self.sizeHint()
        self.setFixedSize(int(hint.width() * 0.9), hint.height())

        # Set custom tab order for a more intuitive workflow.
        # project code -> description -> save button
        self.setTabOrder(self.project_code_input, self.description_input)
        self.setTabOrder(self.description_input, self.save_button)

        self.project_code_input.setFocus()
        self._update_calendar_holidays()

    def _on_date_changed(self, new_date):
        """When the date changes, re-calculate full day times if the box is checked."""
        if self.full_day_checkbox.isChecked():
            self._update_full_day_times()

    def _on_full_day_toggled(self, state):
        """Handles the 'Full Day' checkbox being checked or unchecked."""
        is_checked = (state == Qt.CheckState.Checked.value)
        self.start_time_edit.setEnabled(not is_checked)
        self.end_time_edit.setEnabled(not is_checked)

        if is_checked:
            self.pre_full_day_start_time = self.start_time_edit.time()
            self.pre_full_day_end_time = self.end_time_edit.time()
            self._update_full_day_times()
        else:
            if self.pre_full_day_start_time:
                self.start_time_edit.setTime(self.pre_full_day_start_time)
            if self.pre_full_day_end_time:
                self.end_time_edit.setTime(self.pre_full_day_end_time)

    def _on_copy_previous_task_toggled(self, state):
        is_checked = (state == Qt.CheckState.Checked.value)
        widgets_to_manage = [
            self.project_code_input, self.description_input, self.categories_group,
            self.help_button, self.skip_button,
        ]
        if is_checked:
            if self.previous_task:
                # A previous task exists, so populate the fields
                self.project_code_input.setText(self.previous_task[4])
                self.description_input.setHtml(self.previous_task[5])
                prev_cats = self.previous_task[6].split(',') if self.previous_task[6] else []
                for cb in self.category_checkboxes: cb.setChecked(cb.text() in prev_cats)
                for widget in widgets_to_manage: widget.setEnabled(False)
                self.save_button.setEnabled(True)
            else:
                # No previous task found, show a message and uncheck the box
                QMessageBox.information(self, "No Previous Task", "No previous task was found in the database.")
                self.same_as_prev_checkbox.blockSignals(True)
                self.same_as_prev_checkbox.setChecked(False)
                self.same_as_prev_checkbox.blockSignals(False)
        else: # The box was unchecked by the user
            self.project_code_input.clear()
            self.description_input.clear()
            for cb in self.category_checkboxes:
                cb.setChecked(cb.text() == "QA83")
            for widget in widgets_to_manage: widget.setEnabled(True)
            self._update_save_button_state()

    def save_task(self):
        self._stop_countdown()
        
        start_qtime = self.start_time_edit.time()
        rounded_start_qtime = QTime(start_qtime.hour(), start_qtime.minute(), 0)
        
        end_qtime = self.end_time_edit.time()
        rounded_end_qtime = QTime(end_qtime.hour(), end_qtime.minute(), 0)

        selected_date = self.date_edit.date().toPython()
        task_start_dt = datetime.combine(selected_date, rounded_start_qtime.toPython())
        task_end_dt = datetime.combine(selected_date, rounded_end_qtime.toPython())

        date_str = selected_date.strftime("%Y-%m-%d")
        day_rules = {}
        work_times_row = self.db.get_work_times_for_date(date_str)
        if work_times_row:
            day_rules = {
                'lower': work_times_row[2], 'upper': work_times_row[3],
                'hours': work_times_row[4], 'lunch_s': work_times_row[5],
                'lunch_e': work_times_row[6], 
                'work_days': work_times_row[7].split(','),
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
        
        day_name = selected_date.strftime('%A')
        if date_str in day_rules['holidays'] or day_name not in day_rules['work_days']:
            QMessageBox.warning(self, "Invalid Time", f"Cannot log tasks on a non-working day ({day_name}).")
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

        if task_end_dt <= work_start_dt or task_start_dt >= work_end_dt:
            QMessageBox.warning(self, "Invalid Time", "Task is completely outside of working hours.")
            return
        if task_start_dt >= lunch_start_dt and task_end_dt <= lunch_end_dt:
            QMessageBox.warning(self, "Invalid Time", "Cannot log tasks during lunch hour.")
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
            QMessageBox.warning(self, "Invalid Time", "Task has no duration after adjusting for work/lunch hours.")
            return
        existing_tasks = self.db.get_tasks_for_date(date_str)
        project_code = self.project_code_input.text()
        description = self.description_input.toHtml()
        categories = ",".join([cb.text() for cb in self.category_checkboxes if cb.isChecked()])
        software = "" # Software field is no longer used
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
            QMessageBox.warning(self, "Time Blocked", "The selected time is already fully occupied by other tasks.")
            
    def _update_save_button_state(self):
        project_code_ok = bool(self.project_code_input.text().strip())
        description_ok = bool(self.description_input.toPlainText().strip())
        self.save_button.setEnabled(project_code_ok and description_ok)

    def _update_full_day_times(self):
        """Calculates and sets the start and end times for the selected date."""
        selected_date = self.date_edit.date().toPython()
        boundaries = self._get_workday_boundaries_for_date(selected_date)
        if boundaries:
            start_dt, end_dt = boundaries
            self.start_time_edit.setTime(QTime(start_dt.time()))
            self.end_time_edit.setTime(QTime(end_dt.time()))

    def _get_workday_end_time_for_date(self, selected_date):
        date_str = selected_date.strftime("%Y-%m-%d")
        
        work_times_row = self.db.get_work_times_for_date(date_str)
        if work_times_row:
            day_rules = {
                'lower': work_times_row[2], 'upper': work_times_row[3],
                'hours': work_times_row[4], 'lunch_s': work_times_row[5],
                'lunch_e': work_times_row[6], 
                'work_days': work_times_row[7].split(','),
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

        day_name = selected_date.strftime('%A')
        if date_str in day_rules['holidays'] or day_name not in day_rules['work_days']:
            return None

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

        return work_end_dt.time()

    def _get_workday_boundaries_for_date(self, selected_date):
        """Calculates the effective start and end datetimes for a given date."""
        date_str = selected_date.strftime("%Y-%m-%d")
        
        work_times_row = self.db.get_work_times_for_date(date_str)
        if work_times_row:
            day_rules = {
                'lower': work_times_row[2], 'upper': work_times_row[3],
                'hours': work_times_row[4], 'lunch_s': work_times_row[5],
                'lunch_e': work_times_row[6], 
                'work_days': work_times_row[7].split(','),
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

        day_name = selected_date.strftime('%A')
        if date_str in day_rules['holidays'] or day_name not in day_rules['work_days']:
            return None

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
        work_end_dt = work_start_dt + timedelta(hours=day_rules['hours']) + (datetime.combine(selected_date, time.fromisoformat(day_rules['lunch_e'])) - datetime.combine(selected_date, time.fromisoformat(day_rules['lunch_s'])))
        return work_start_dt, work_end_dt

    def set_initial_values(self):
        self.date_edit.setDate(QDate.currentDate())
        now = QTime.currentTime()
        temp_time = now.addSecs(30)
        rounded_now = QTime(temp_time.hour(), temp_time.minute(), 0)

        selected_date_obj = self.date_edit.date().toPython()
        workday_end_time_py = self._get_workday_end_time_for_date(selected_date_obj)

        final_end_time = rounded_now
        if workday_end_time_py:
            workday_end_qtime = QTime(workday_end_time_py.hour, workday_end_time_py.minute, workday_end_time_py.second)
            final_end_time = min(rounded_now, workday_end_qtime)
        
        self.end_time_edit.setTime(final_end_time)

    def skip_task(self):
        self._stop_countdown()
        self.reject()

class EditTaskPopup(Popup):
    def __init__(self, db, config, task_data, parent=None):
        # Call the parent constructor. This will initialize the UI, set initial values,
        # and crucially, install the event filters that handle Ctrl+B/I/U.
        # We pass previous_task=None as it's not relevant for editing, and
        # is_manual_trigger=True to disable the countdown timer.
        super().__init__(db=db, previous_task=None, config=config, parent=parent, is_manual_trigger=True)

        # Store task-specific data
        self.task_data = task_data
        self.task_id = task_data[0]
        
        # Override the title set by the parent
        self.original_title = "Edit Task"
        self.setWindowTitle(self.original_title)
        
        # The parent's __init__ called init_ui() and set_initial_values().
        # Now we load the actual task data, overwriting the initial values.
        self.load_task_data()

        # Hide/modify widgets that are not needed for editing
        self.same_as_prev_checkbox.hide()
        self.skip_button.hide()
        self.save_button.setText("Save Changes (Ctrl+⏎)")
        self.countdown_stopped = True

    def load_task_data(self):
        """Loads the existing task data into the dialog's widgets."""
        _, task_date, start_time, end_time, proj_code, desc, cats, soft, _, _ = self.task_data

        self.date_edit.setDate(QDate.fromString(task_date, "yyyy-MM-dd"))
        self.start_time_edit.setTime(QTime.fromString(start_time, "HH:mm:ss"))
        self.end_time_edit.setTime(QTime.fromString(end_time, "HH:mm:ss"))
        self.project_code_input.setText(proj_code)
        self.description_input.setHtml(desc)

        cat_list = cats.split(',') if cats else []
        for cb in self.category_checkboxes:
            cb.setChecked(cb.text() in cat_list)
    
    def save_task(self):
        """Saves the changes to the existing task after validation."""
        self._stop_countdown()

        start_qtime = self.start_time_edit.time()
        end_qtime = self.end_time_edit.time()
        project_code = self.project_code_input.text().strip()
        description = self.description_input.toHtml()
        categories = ",".join([cb.text() for cb in self.category_checkboxes if cb.isChecked()])

        if not project_code or not self.description_input.toPlainText().strip():
            QMessageBox.warning(self, "Input Error", "Project Code and Description cannot be empty.")
            return

        if end_qtime <= start_qtime:
            QMessageBox.warning(self, "Invalid Time", "End time must be after start time.")
            return

        selected_date = self.date_edit.date().toPython()
        date_str = selected_date.strftime("%Y-%m-%d")
        
        other_tasks = [t for t in self.db.get_tasks_for_date(date_str) if t[0] != self.task_id]

        new_start_dt = datetime.combine(selected_date, start_qtime.toPython())
        new_end_dt = datetime.combine(selected_date, end_qtime.toPython())

        for task_row in other_tasks:
            existing_start = datetime.combine(selected_date, time.fromisoformat(task_row[2]))
            existing_end = datetime.combine(selected_date, time.fromisoformat(task_row[3]))
            if new_start_dt < existing_end and new_end_dt > existing_start:
                QMessageBox.warning(self, "Time Conflict", "The new time for this task overlaps with another existing task.")
                return

        data = {
            'start_time': start_qtime.toString("HH:mm:ss"), 'end_time': end_qtime.toString("HH:mm:ss"),
            'project_code': project_code, 'description': description,
            'categories': categories, 'software': ""
        }

        self.db.update_task_by_id(self.task_id, data)
        self.accept()