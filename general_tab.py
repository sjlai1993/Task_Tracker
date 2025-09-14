# general_tab.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QListWidget, QListWidgetItem, QDateEdit,
                             QGroupBox, QGridLayout, QCalendarWidget, QStyle,
                             QApplication, QMessageBox, QSystemTrayIcon, QDialog, QMenu,
                             QTimeEdit, QDialogButtonBox, QListWidget)
from PySide6.QtCore import Qt, QSize, QDate, QTime, QEvent
from PySide6.QtGui import QColor, QTextCharFormat, QTextDocument, QAction
from datetime import datetime, time, timedelta
from popup import EditTaskPopup

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
        self.task_list_widget.setWordWrap(True)
        self.task_list_widget.viewport().installEventFilter(self)
        self.task_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.task_list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.task_list_widget)

        button_layout = QHBoxLayout()
        self.copy_button = QPushButton("Duplicate Task")
        self.copy_button.setToolTip("Create a new task for today using the selected task as a template")
        self.copy_button.clicked.connect(self._copy_selected_task)
        button_layout.addWidget(self.copy_button)

        self.edit_button = QPushButton("Edit Task")
        self.edit_button.setToolTip("Edit the selected task")
        self.edit_button.clicked.connect(self._edit_selected_task)
        button_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Task")
        self.delete_button.setToolTip("Delete the selected task")
        self.delete_button.clicked.connect(self._delete_selected_task)
        button_layout.addWidget(self.delete_button)

        button_layout.addStretch()

        set_start_time_button = QPushButton("Set Day's Start Time")
        set_start_time_button.setToolTip("Manually override the start time for the selected day.")
        set_start_time_button.clicked.connect(self._override_start_time)
        button_layout.addWidget(set_start_time_button)

        log_task_button = QPushButton("Log Task")
        log_task_button.clicked.connect(self._on_log_task_clicked)
        button_layout.addWidget(log_task_button)
        
        layout.addLayout(button_layout)

        self.task_list_widget.itemSelectionChanged.connect(self._update_button_states)
        self._update_button_states()

    def eventFilter(self, source, event):
        """
        Filters events to capture left-button double-clicks on the task list,
        ignoring double-clicks from other buttons.
        """
        if source is self.task_list_widget.viewport() and event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                item = self.task_list_widget.itemAt(event.pos())
                if item:
                    self._on_item_double_clicked(item)
                    return True # Event was handled
        return super().eventFilter(source, event)

    def _show_context_menu(self, position):
        """Creates and shows a context-sensitive menu on right-click."""
        item = self.task_list_widget.itemAt(position)
        menu = QMenu(self.task_list_widget)

        task_data = item.data(Qt.ItemDataRole.UserRole) if item else None
        unrecorded_slot_data = item.data(Qt.ItemDataRole.UserRole + 1) if item else None

        # --- Log Task Action ---
        log_action = QAction("Log Task", self)
        if unrecorded_slot_data:
            # If right-clicking an unrecorded slot, log for that specific slot
            log_action.triggered.connect(lambda: self._log_unrecorded_slot(unrecorded_slot_data))
        else:
            # Generic log task action
            log_action.triggered.connect(self.parent_window.manual_popup)
        menu.addAction(log_action)

        # --- Actions for Recorded Tasks ---
        if task_data:
            #menu.addSeparator()

            edit_action = QAction("Edit Task", self)
            edit_action.triggered.connect(lambda: self._edit_task(task_data[0]))
            menu.addAction(edit_action)

            delete_action = QAction("Delete Task", self)
            delete_action.triggered.connect(lambda: self._delete_task(task_data[0], task_data[4]))
            menu.addAction(delete_action)

            copy_action = QAction("Duplicate Task", self)
            copy_action.triggered.connect(lambda: self.parent_window.popup_from_copied_task(task_data))
            menu.addAction(copy_action)

        menu.exec(self.task_list_widget.viewport().mapToGlobal(position))

    def _log_unrecorded_slot(self, unrecorded_slot_data):
        """Helper function to trigger the log popup for a specific unrecorded slot."""
        start_dt, end_dt = unrecorded_slot_data
        has_subsequent_task = False
        for i in range(self.task_list_widget.count()):
            item = self.task_list_widget.item(i)
            task_data = item.data(Qt.ItemDataRole.UserRole)
            if task_data and time.fromisoformat(task_data[2]) == end_dt.time():
                has_subsequent_task = True
                break
        self.parent_window.manual_popup(
            start_time=start_dt.time(), end_time=end_dt.time(), has_subsequent_task=has_subsequent_task
        )

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

    def _override_start_time(self):
        date_str = self.view_date.strftime("%Y-%m-%d")
        day_name = self.view_date.strftime('%A')
        
        is_holiday = date_str in self.config.get('holidays', [])
        is_non_working_day = day_name not in self.config.get('working_days', [])

        if is_holiday or is_non_working_day:
            QMessageBox.information(self, "Action Not Available", "Cannot set start time on a non-working day or holiday.")
            return

        work_times_row = self.db.get_work_times_for_date(date_str)
        tasks = self.db.get_tasks_for_date(date_str)
        current_start_t = None
        
        # =====================================================================
        # === MODIFIED SECTION START (Add constraints to override dialog) ===
        # =====================================================================
        lower_bound_str, upper_bound_str = None, None
        if work_times_row:
            current_start_t = time.fromisoformat(work_times_row[1])
            lower_bound_str = work_times_row[2]
            upper_bound_str = work_times_row[3]
        else: 
            lower_bound_str = self.config['work_start_time_flexible']['lower']
            upper_bound_str = self.config['work_start_time_flexible']['upper']
            if tasks:
                earliest_task_t = time.fromisoformat(tasks[0][2])
                lower_bound_t = time.fromisoformat(lower_bound_str)
                upper_bound_t = time.fromisoformat(upper_bound_str)
                current_start_t = earliest_task_t if lower_bound_t <= earliest_task_t <= upper_bound_t else upper_bound_t
            else:
                current_start_t = time.fromisoformat(upper_bound_str)

        lower_bound_qtime = QTime.fromString(lower_bound_str, "HH:mm:ss")
        upper_bound_qtime = QTime.fromString(upper_bound_str, "HH:mm:ss")
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Override Start Time")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Select new start time for {self.view_date.strftime('%d/%m/%Y')}:"))
        time_edit = QTimeEdit()
        time_edit.setTimeRange(lower_bound_qtime, upper_bound_qtime)
        time_edit.setTime(QTime(current_start_t))
        layout.addWidget(time_edit)
        hint_label = QLabel(f"<i>Time must be between {lower_bound_qtime.toString('HH:mm')} and {upper_bound_qtime.toString('HH:mm')}.</i>")
        hint_label.setStyleSheet("font-size: 9px; color: gray;")
        layout.addWidget(hint_label)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        # =====================================================================
        # === MODIFIED SECTION END ===
        # =====================================================================
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec():
            new_start_time = time_edit.time()
            new_start_time_str = new_start_time.toString("HH:mm:ss")

            rows_affected = self.db.set_effective_start_time(date_str, new_start_time_str)
            
            if rows_affected == 0:
                settings_snapshot = {
                    'work_start_lower': self.config['work_start_time_flexible']['lower'],
                    'work_start_upper': self.config['work_start_time_flexible']['upper'],
                    'daily_working_hours': self.config['daily_working_hours'],
                    'lunch_start': self.config['lunch_hour']['start'],
                    'lunch_end': self.config['lunch_hour']['end'],
                    'working_days': self.config['working_days'],
                    'holidays': self.config.get('holidays', [])
                }
                self.db.add_work_times(date_str, new_start_time_str, settings_snapshot)

            QMessageBox.information(self, "Success", f"Start time for {date_str} has been updated to {new_start_time.toString('HH:mm')}.")
            self.update_task_view()

    def _on_date_picker_changed(self, new_qdate):
        self.view_date = new_qdate.toPython()
        self.update_task_view()

    def _go_to_previous_day(self):
        self.view_date -= timedelta(days=1)
        self.update_task_view()

    def _go_to_next_day(self):
        self.view_date += timedelta(days=1)
        self.update_task_view()

    def _create_item_widget(self, rich_text):
        item_widget = QWidget()
        main_layout = QHBoxLayout(item_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        label = QLabel(rich_text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(label, 1)

        return item_widget

    def _update_button_states(self):
        selected_items = self.task_list_widget.selectedItems()
        is_task_selected = False
        if len(selected_items) == 1:
            item = selected_items[0]
            if item.data(Qt.ItemDataRole.UserRole):
                is_task_selected = True
        
        self.copy_button.setEnabled(is_task_selected)
        self.edit_button.setEnabled(is_task_selected)
        self.delete_button.setEnabled(is_task_selected)

    def _get_selected_task_data(self):
        selected_items = self.task_list_widget.selectedItems()
        if not selected_items:
            return None
        return selected_items[0].data(Qt.ItemDataRole.UserRole)
    
    def _get_selected_unrecorded_slot_data(self):
        selected_items = self.task_list_widget.selectedItems()
        if not selected_items:
            return None
        return selected_items[0].data(Qt.ItemDataRole.UserRole + 1)

    def _on_log_task_clicked(self):
        unrecorded_slot_data = self._get_selected_unrecorded_slot_data()
        if unrecorded_slot_data:
            start_dt, end_dt = unrecorded_slot_data
            
            has_subsequent_task = False
            for i in range(self.task_list_widget.count()):
                item = self.task_list_widget.item(i)
                task_data = item.data(Qt.ItemDataRole.UserRole)
                if task_data:
                    task_start_time = time.fromisoformat(task_data[2])
                    if task_start_time == end_dt.time():
                        has_subsequent_task = True
                        break
            
            self.parent_window.manual_popup(
                start_time=start_dt.time(), 
                end_time=end_dt.time(), 
                has_subsequent_task=has_subsequent_task
            )
        else:
            self.parent_window.manual_popup()

    def _on_item_double_clicked(self, item):
        """Handles double-clicking on an item in the task list."""
        task_data = item.data(Qt.ItemDataRole.UserRole)
        unrecorded_slot_data = item.data(Qt.ItemDataRole.UserRole + 1)

        if task_data:
            # It's a recorded task, open the edit popup.
            self._edit_task(task_data[0])
        elif unrecorded_slot_data:
            self._log_unrecorded_slot(unrecorded_slot_data)

    def _copy_selected_task(self):
        task_data = self._get_selected_task_data()
        if task_data:
            self.parent_window.popup_from_copied_task(task_data)

    def _edit_selected_task(self):
        task_data = self._get_selected_task_data()
        if task_data:
            self._edit_task(task_data[0])
            
    def _delete_selected_task(self):
        task_data = self._get_selected_task_data()
        if task_data:
            self._delete_task(task_data[0], task_data[4])

    def _edit_task(self, task_id):
        task_data = self.db.get_task_by_id(task_id)
        if not task_data:
            QMessageBox.critical(self, "Error", "Could not find the selected task in the database.")
            return

        edit_popup = EditTaskPopup(self.db, self.config, task_data, parent=self)
        if edit_popup.exec() == QDialog.DialogCode.Accepted:
            self.update_task_view()
            if hasattr(self.parent_window, 'qa83_tab'):
                self.parent_window.qa83_tab.update_qa83_view()

    def _copy_task_to_new_popup(self, task_data):
        self.parent_window.popup_from_copied_task(task_data)

    def _add_recorded_task_item(self, task, is_day_off):
        start_dt = datetime.combine(self.view_date, time.fromisoformat(task[2]))
        end_dt = datetime.combine(self.view_date, time.fromisoformat(task[3]))
        project_code = task[4]
        description_html = task[5]
        
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        start_str = start_dt.strftime("%H:%M")
        end_str = end_dt.strftime("%H:%M")
        rich_text = (f"<b>{start_str} - {end_str} ({duration_hours:.2f}h)</b>"
                     f" | <b>{project_code}</b> | {description_html}")
        
        widget = self._create_item_widget(rich_text)
        
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, task)
        item.setSizeHint(widget.sizeHint())
        self.task_list_widget.addItem(item)
        self.task_list_widget.setItemWidget(item, widget)

    def _add_unrecorded_task_item(self, start_dt, end_dt, is_day_off):
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        start_str = start_dt.strftime("%H:%M")
        end_str = end_dt.strftime("%H:%M")
        rich_text = (f"<b>{start_str} - {end_str} ({duration_hours:.2f}h)</b>"
                     f" | <b>---</b> | <i>Unrecorded</i>")
                     
        widget = self._create_item_widget(rich_text)

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, None) 
        item.setData(Qt.ItemDataRole.UserRole + 1, (start_dt, end_dt)) 
        item.setSizeHint(widget.sizeHint())
        self.task_list_widget.addItem(item)
        self.task_list_widget.setItemWidget(item, widget)

    def update_task_view(self):
        self.date_picker.blockSignals(True)
        self.date_picker.setDate(QDate(self.view_date))
        self.date_picker.blockSignals(False)
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

    def _delete_task(self, task_id, project_code):
        child_task_ids = self.db.get_child_task_ids(task_id)

        if child_task_ids:
            reply = QMessageBox.warning(self, "Confirm Delete Master Task",
                f"This task is a master for <b>{len(child_task_ids)} other task(s)</b>.<br><br>"
                f"Deleting it will unmerge all associated tasks.<br><br>"
                f"Are you sure you want to delete this master task for project '{project_code}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
        else:
            reply = QMessageBox.question(self, "Confirm Delete",
                f"Are you sure you want to delete the task for project '{project_code}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if child_task_ids:
                self.db.unmerge_specific_tasks(child_task_ids)

            self.db.delete_task_by_id(task_id)
            self.update_task_view()
            
            if hasattr(self.parent_window, 'qa83_tab'):
                self.parent_window.qa83_tab.update_qa83_view()