# qa83_tab.py

import json
import os
import sys  # <--- ADDED IMPORT
from collections import defaultdict
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTableWidget, QTableWidgetItem, QDialog,
                             QGroupBox, QGridLayout, QCalendarWidget, QHeaderView,
                             QAbstractItemView, QLineEdit, QFormLayout, QComboBox,
                             QTextEdit, QMessageBox, QFileDialog, QListWidget, QListWidgetItem,
                             QCheckBox, QSizePolicy)
from PySide6.QtCore import Qt, QDate, QUrl, QEvent, QTimer, QStandardPaths
from PySide6.QtGui import QTextDocument, QIntValidator, QKeySequence, QDesktopServices, QFont
from datetime import datetime, time
import calendar
from timesheet_tab import CopyableTableWidget

class QA83SettingsDialog(QDialog):
    """Dialog to edit name and designation for QA83 reports."""
    def __init__(self, current_name, current_designation, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QA83 Report Settings")
        layout = QFormLayout(self)
        self.name_input = QLineEdit(current_name)
        self.designation_input = QLineEdit(current_designation)
        layout.addRow("Name:", self.name_input); layout.addRow("Designation:", self.designation_input)
        button_box = QHBoxLayout(); ok_button = QPushButton("Save"); ok_button.setDefault(True); ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel"); cancel_button.clicked.connect(self.reject)
        button_box.addStretch(); button_box.addWidget(cancel_button); button_box.addWidget(ok_button); layout.addRow(button_box)
    def get_values(self): return self.name_input.text(), self.designation_input.text()

class ProjectTitleDialog(QDialog):
    def __init__(self, project_code, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Project Title"); layout = QFormLayout(self)
        layout.addRow(QLabel(f"No title found for project code: <b>{project_code}</b>")); self.title_input = QLineEdit()
        layout.addRow("Project Title:", self.title_input); button_box = QHBoxLayout()
        ok_button = QPushButton("Save Title"); ok_button.setDefault(True); ok_button.clicked.connect(self.accept)
        button_box.addStretch(); button_box.addWidget(ok_button); layout.addRow(button_box); self.title_input.setFocus()
    def get_title(self): return self.title_input.text().strip()

class MergeTasksDialog(QDialog):
    def __init__(self, task_groups, parent=None):
        super().__init__(parent)
        self.task_groups = task_groups
        self.setWindowTitle("Merge Tasks")
        self.setMinimumWidth(450)
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.master_task_combo = QComboBox()
        all_descriptions_html = []
        for proj_code, html_desc in self.task_groups:
            doc = QTextDocument()
            doc.setHtml(html_desc)
            self.master_task_combo.addItem(f"{proj_code} - {doc.toPlainText()[:80]}...")
            all_descriptions_html.append(html_desc)

        self.merged_desc_input = QTextEdit()
        self.merged_desc_input.setHtml("".join(all_descriptions_html))
        self.merged_desc_input.setFixedHeight(100)
        
        self.merged_desc_input.installEventFilter(self)

        form_layout.addRow("Select Master Task:", self.master_task_combo)
        form_layout.addRow("New Merged Description:", self.merged_desc_input)
        layout.addLayout(form_layout)

        button_box = QHBoxLayout()
        ok_button = QPushButton("Merge")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addStretch()
        button_box.addWidget(cancel_button)
        button_box.addWidget(ok_button)
        layout.addLayout(button_box)

    def eventFilter(self, watched_object, event):
        if event.type() == QEvent.Type.KeyPress:
            if watched_object is self.merged_desc_input:
                if event.matches(QKeySequence.StandardKey.Bold):
                    self._format_bold()
                    return True
                if event.matches(QKeySequence.StandardKey.Italic):
                    self._format_italic()
                    return True
                if event.matches(QKeySequence.StandardKey.Underline):
                    self._format_underline()
                    return True
        return super().eventFilter(watched_object, event)

    def _format_bold(self):
        cursor = self.merged_desc_input.textCursor()
        fmt = cursor.charFormat()
        is_bold = fmt.fontWeight() == QFont.Weight.Bold
        fmt.setFontWeight(QFont.Weight.Normal if is_bold else QFont.Weight.Bold)
        cursor.mergeCharFormat(fmt)
        self.merged_desc_input.setFocus()

    def _format_italic(self):
        cursor = self.merged_desc_input.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        cursor.mergeCharFormat(fmt)
        self.merged_desc_input.setFocus()

    def _format_underline(self):
        cursor = self.merged_desc_input.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        cursor.mergeCharFormat(fmt)
        self.merged_desc_input.setFocus()

    def get_selection(self):
        master_index = self.master_task_combo.currentIndex()
        merged_description_html = ""
        if self.merged_desc_input.toPlainText().strip():
            merged_description_html = self.merged_desc_input.toHtml()
        
        return self.task_groups[master_index], merged_description_html

class OverrideDescriptionDialog(QDialog):
    def __init__(self, current_description_html, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Override Task Description")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        
        self.description_input = QTextEdit()
        self.description_input.setHtml(current_description_html)
        self.description_input.installEventFilter(self)
        layout.addWidget(self.description_input)

        button_box = QHBoxLayout()
        ok_button = QPushButton("Save")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addStretch()
        button_box.addWidget(cancel_button)
        button_box.addWidget(ok_button)
        layout.addLayout(button_box)

    def eventFilter(self, watched_object, event):
        if event.type() == QEvent.Type.KeyPress:
            if watched_object is self.description_input:
                if event.matches(QKeySequence.StandardKey.Bold): self._format_bold(); return True
                if event.matches(QKeySequence.StandardKey.Italic): self._format_italic(); return True
                if event.matches(QKeySequence.StandardKey.Underline): self._format_underline(); return True
        return super().eventFilter(watched_object, event)

    def _format_bold(self):
        cursor = self.description_input.textCursor()
        fmt = cursor.charFormat(); is_bold = fmt.fontWeight() == QFont.Weight.Bold
        fmt.setFontWeight(QFont.Weight.Normal if is_bold else QFont.Weight.Bold)
        cursor.mergeCharFormat(fmt); self.description_input.setFocus()

    def _format_italic(self):
        cursor = self.description_input.textCursor()
        fmt = cursor.charFormat(); fmt.setFontItalic(not fmt.fontItalic())
        cursor.mergeCharFormat(fmt); self.description_input.setFocus()

    def _format_underline(self):
        cursor = self.description_input.textCursor()
        fmt = cursor.charFormat(); fmt.setFontUnderline(not fmt.fontUnderline())
        cursor.mergeCharFormat(fmt); self.description_input.setFocus()

    def get_description(self):
        """Returns the new HTML description, or an empty string if the input is empty to signify reversion."""
        new_desc = self.description_input.toHtml()
        # A cleared QTextEdit still contains HTML boilerplate. Check if it's effectively empty.
        doc = QTextDocument()
        doc.setHtml(new_desc)
        # If the plain text is empty, return an empty string to clear the override.
        return new_desc if doc.toPlainText().strip() else ""

class ProgressInputDialog(QDialog):
    def __init__(self, project_code, description, current_start_progress, current_final_progress, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Task Progress")
        
        main_layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        form_layout.addRow(QLabel(f"<b>Project:</b> {project_code}"))
        form_layout.addRow(QLabel(f"<b>Task:</b> {description}"))
        
        self.start_progress_input = QLineEdit()
        self.start_progress_input.setText(current_start_progress)
        form_layout.addRow("Progress at Start of Month (%):", self.start_progress_input)

        self.progress_input = QLineEdit()
        self.progress_input.setText(current_final_progress)
        form_layout.addRow("Final Cumulative Progress (%):", self.progress_input)
        
        hint_label = QLabel("<i>Enter a value from 0-100, or '-' for a recurring task.</i>")
        hint_label.setStyleSheet("font-size: 9px; color: gray;")
        form_layout.addRow("", hint_label)
        
        self.validator = QIntValidator(0, 100, self)
        self.progress_input.textChanged.connect(self.validate_input)
        self.start_progress_input.setValidator(QIntValidator(0, 100, self))

        button_box = QHBoxLayout()
        ok_button = QPushButton("OK (Ctrl+Enter)")
        ok_button.setDefault(True)
        ok_button.setShortcut(QKeySequence("Ctrl+Return"))
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addStretch()
        button_box.addWidget(cancel_button)
        button_box.addWidget(ok_button)
        
        main_layout.addLayout(form_layout)
        main_layout.addLayout(button_box)
        self.setLayout(main_layout)

    def validate_input(self, text):
        if text == "-": return
        self.validator.validate(text, 0)[0]

    def get_values(self):
        start_text = self.start_progress_input.text().strip()
        try:
            start_progress = str(max(0, min(100, int(start_text))))
        except ValueError:
            start_progress = "0"

        final_text = self.progress_input.text().strip()
        if final_text == "-":
            final_progress = "-"
        else:
            try:
                final_progress = str(max(0, min(100, int(final_text))))
            except ValueError:
                final_progress = "100"
        
        return start_progress, final_progress

class EditMergedTaskDialog(QDialog):
    def __init__(self, master_id, db, parent=None):
        super().__init__(parent)
        self.master_id = master_id
        self.db = db
        self.setWindowTitle("Edit Merged Task")
        self.setMinimumWidth(500)

        self.tasks_in_group = self.db.get_tasks_for_master_group(self.master_id)
        master_task = next((t for t in self.tasks_in_group if t[0] == self.master_id), None)
        
        if not master_task:
            QMessageBox.critical(self, "Error", "Could not find the master task for this group.")
            QTimer.singleShot(0, self.reject)
            return
            
        layout = QVBoxLayout(self)
        
        desc_group = QGroupBox("Merged Description")
        desc_layout = QVBoxLayout(desc_group)
        self.merged_desc_input = QTextEdit()
        self.merged_desc_input.setPlaceholderText("Edit the merged description... (Ctrl+B/I/U for formatting)")
        self.merged_desc_input.setHtml(master_task[9] or master_task[5])
        self.merged_desc_input.installEventFilter(self)
        desc_layout.addWidget(self.merged_desc_input)
        layout.addWidget(desc_group)

        unmerge_group = QGroupBox("Select Tasks to Unmerge")
        unmerge_layout = QVBoxLayout(unmerge_group)
        self.task_list = QListWidget()
        for task in self.tasks_in_group:
            if task[0] == self.master_id: continue
            
            doc = QTextDocument()
            doc.setHtml(task[5])
            
            item_text = f"[{task[1]}] {doc.toPlainText()[:100]}"
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, task[0])
            self.task_list.addItem(item)
        unmerge_layout.addWidget(self.task_list)
        layout.addWidget(unmerge_group)

        button_box = QHBoxLayout()
        ok_button = QPushButton("Save Changes")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addStretch()
        button_box.addWidget(cancel_button)
        button_box.addWidget(ok_button)
        layout.addLayout(button_box)

    def eventFilter(self, watched_object, event):
        if event.type() == QEvent.Type.KeyPress:
            if watched_object is self.merged_desc_input:
                if event.matches(QKeySequence.StandardKey.Bold):
                    self._format_bold()
                    return True
                if event.matches(QKeySequence.StandardKey.Italic):
                    self._format_italic()
                    return True
                if event.matches(QKeySequence.StandardKey.Underline):
                    self._format_underline()
                    return True
        return super().eventFilter(watched_object, event)

    def _format_bold(self):
        cursor = self.merged_desc_input.textCursor()
        fmt = cursor.charFormat()
        is_bold = fmt.fontWeight() == QFont.Weight.Bold
        fmt.setFontWeight(QFont.Weight.Normal if is_bold else QFont.Weight.Bold)
        cursor.mergeCharFormat(fmt)
        self.merged_desc_input.setFocus()

    def _format_italic(self):
        cursor = self.merged_desc_input.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        cursor.mergeCharFormat(fmt)
        self.merged_desc_input.setFocus()

    def _format_underline(self):
        cursor = self.merged_desc_input.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        cursor.mergeCharFormat(fmt)
        self.merged_desc_input.setFocus()

    def get_changes(self):
        new_description = self.merged_desc_input.toHtml()
        
        ids_to_unmerge = []
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                ids_to_unmerge.append(item.data(Qt.ItemDataRole.UserRole))
        
        # Return the total number of children as well, to check if all are being unmerged.
        total_children = self.task_list.count()

        return new_description, ids_to_unmerge, total_children

class QA83Tab(QWidget):
    CONFIG_FILE = 'QA83.json'

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db; self.view_date = datetime.now().date(); self.qa83_config = self._load_config()
        self.init_ui(); self.update_qa83_view()

    def _load_config(self):
        if not os.path.exists(self.CONFIG_FILE):
            default_config = {"qa83_categories": ["QA83"], "name": "Your Name", "designation": "Your Designation"}
            with open(self.CONFIG_FILE, 'w') as f: json.dump(default_config, f, indent=2); return default_config
        try:
            with open(self.CONFIG_FILE, 'r') as f: config = json.load(f)
            config.setdefault("name", "Your Name"); config.setdefault("designation", "Your Designation"); return config
        except (json.JSONDecodeError, FileNotFoundError): return {"qa83_categories": [], "name": "", "designation": ""}

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        nav_group = QGroupBox("Month Navigation"); nav_layout = QGridLayout(nav_group); prev_button = QPushButton("<"); prev_button.clicked.connect(self._go_to_previous_month)
        self.month_label = QLabel(); self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.month_label.setStyleSheet("QLabel { border: 1px solid gray; border-radius: 4px; padding: 4px; }"); self.month_label.mousePressEvent = self._show_calendar_picker
        next_button = QPushButton(">"); next_button.clicked.connect(self._go_to_next_month); nav_layout.addWidget(prev_button, 0, 0); nav_layout.addWidget(self.month_label, 0, 1); nav_layout.addWidget(next_button, 0, 2); nav_layout.setColumnStretch(1, 1); main_layout.addWidget(nav_group)
        self.table = CopyableTableWidget(); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) 
        self.table.setStyleSheet("QTableWidget::item:selected { background-color: #447ED0; color: white; }"); header = self.table.horizontalHeader(); header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents); header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents); header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch); header.setHighlightSections(False)
        main_layout.addWidget(self.table); button_layout = QHBoxLayout()
        
        # This ensures that row heights automatically adjust to fit their content.
        # Setting this to Interactive allows the user to manually resize rows.
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        self.unassign_qa83_button = QPushButton("Unassign QA83")
        self.unassign_qa83_button.clicked.connect(self._unassign_qa83_tag)
        button_layout.addWidget(self.unassign_qa83_button)
        
        self.edit_merged_task_button = QPushButton("Edit Merged Task")
        self.edit_merged_task_button.clicked.connect(self._edit_merged_task)
        button_layout.addWidget(self.edit_merged_task_button)

        self.override_desc_button = QPushButton("Override Description")
        self.override_desc_button.clicked.connect(self._on_override_description_clicked)
        button_layout.addWidget(self.override_desc_button)

        button_layout.addStretch()
        
        self.merge_button = QPushButton("Merge Selected Tasks"); self.merge_button.clicked.connect(self._merge_selected_tasks)
        self.set_progress_button = QPushButton("Set Task Progress"); self.set_progress_button.clicked.connect(self._set_task_progress)
        generate_report_button = QPushButton("Generate HTML Report"); generate_report_button.clicked.connect(self._generate_html_report)
        self.table.itemSelectionChanged.connect(self._update_button_states)
        button_layout.addWidget(self.merge_button)
        button_layout.addWidget(self.set_progress_button)
        button_layout.addWidget(generate_report_button)
        main_layout.addLayout(button_layout)
        self._update_button_states()

    def _on_override_description_clicked(self):
        """Handler for the 'Override Description' button."""
        selected_rows = list(set(index.row() for index in self.table.selectedIndexes()))
        if len(selected_rows) == 1:
            self._override_description(selected_rows[0])
            
    def _override_description(self, row):
        """Opens a dialog to override the description for a task group."""
        desc_item = self.table.item(row, 2)
        if not desc_item: return

        group_id = desc_item.data(Qt.ItemDataRole.UserRole + 2)
        if not group_id:
            QMessageBox.warning(self, "Error", "Could not identify the task group.")
            return

        master_task = self.db.get_task_by_id(group_id)
        current_desc_html = master_task[9] or master_task[5]

        dialog = OverrideDescriptionDialog(current_desc_html, self)
        if dialog.exec():
            self.db.set_merged_description(group_id, dialog.get_description()); self.update_qa83_view()

    def handle_tab_focus(self):
        month_year_str = self.view_date.strftime('%Y-%m'); all_tasks = self.db.get_tasks_for_month_with_master_info(month_year_str); qa83_categories = set(self.qa83_config.get("qa83_categories", []))
        qa83_tasks = [task for task in all_tasks if qa83_categories.intersection(set(task[6].split(',')))]; unique_proj_codes = set()
        for task in qa83_tasks:
            master_id = task[8]
            if master_id:
                master_task = next((t for t in all_tasks if t[0] == master_id), None)
                if master_task: unique_proj_codes.add(master_task[4])
            else: unique_proj_codes.add(task[4])
        titles_were_added = False
        for code in sorted(list(unique_proj_codes)):
            if not self.db.get_project_title(code):
                dialog = ProjectTitleDialog(code, self)
                if dialog.exec():
                    title = dialog.get_title()
                    if title: self.db.set_project_title(code, title); titles_were_added = True
        
        # Always update the view after checking for titles.
        self.update_qa83_view()

    def _open_settings(self):
        current_name = self.qa83_config.get("name", ""); current_designation = self.qa83_config.get("designation", "")
        dialog = QA83SettingsDialog(current_name, current_designation, self)
        if dialog.exec():
            name, designation = dialog.get_values(); self.qa83_config["name"] = name; self.qa83_config["designation"] = designation
            with open(self.CONFIG_FILE, 'w') as f: json.dump(self.qa83_config, f, indent=2)
            QMessageBox.information(self, "Settings Saved", "QA83 report settings updated.")

    def _generate_html_report(self):
        desktop_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        default_filename = f"QA83_Report_{self.view_date.strftime('%Y-%m')}.html"
        default_save_path = os.path.join(desktop_path, default_filename)
        
        save_path, _ = QFileDialog.getSaveFileName(self, "Save HTML Report", default_save_path, "HTML Files (*.html)")
        if not save_path: return
        
        _, _, num_weeks = self._get_month_weeks_info(self.view_date.year, self.view_date.month)
        
        template_filename = 'report_template_six.html' if num_weeks == 6 else 'report_template.html'
        
        # =====================================================================
        # === MODIFIED SECTION START (Robust path resolution) ===
        # =====================================================================
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundled executable, the base path is the executable's directory.
            base_path = os.path.dirname(sys.executable)
        else:
            # If the application is run as a script, the base path is the script's directory.
            base_path = os.path.dirname(os.path.realpath(__file__))
        
        template_path = os.path.join(base_path, template_filename)
        # =====================================================================
        # === MODIFIED SECTION END ===
        # =====================================================================

        try:
            with open(template_path, 'r', encoding='utf-8') as f: template_content = f.read()
        except FileNotFoundError: QMessageBox.critical(self, "Error", f"Template file not found at:\n{template_path}"); return
        name = self.qa83_config.get("name", "N/A"); designation = self.qa83_config.get("designation", "N/A"); month_year = self.view_date.strftime('%B %Y')
        rows_html_list = []
        description_counter = 0
        for row in range(self.table.rowCount()):
            row_html = "<tr>"
            if self.table.item(row, 0):
                description_counter = 1
                rowspan = self.table.rowSpan(row, 0); proj_code = self.table.item(row, 0).text(); proj_title = self.table.item(row, 1).text();
                row_html += f'<td class="proj-code" rowspan="{rowspan}">{proj_code}</td>'
                row_html += f'<td class="title" rowspan="{rowspan}">{proj_title}</td>'
            
            desc_widget = self.table.cellWidget(row, 2); desc_text = ""
            if desc_widget and isinstance(desc_widget, QLabel):
                html_content = desc_widget.text()
                
                p_tag_pos = html_content.lower().find('<p')
                
                if p_tag_pos != -1:
                    first_tag_end = html_content.find('>', p_tag_pos)
                    if first_tag_end != -1:
                        desc_text = (f"{html_content[:first_tag_end + 1]}"
                                     f"{description_counter}) "
                                     f"{html_content[first_tag_end + 1:]}")
                    else:
                        desc_text = f"{description_counter}) {html_content}"
                else:
                    desc_text = f"{description_counter}) {html_content}"

                description_counter += 1

            row_html += f'<td class="desc">{desc_text}</td>'
            for col in range(3, self.table.columnCount()):
                item = self.table.item(row, col); cell_text = item.text() if item else ""; row_html += f'<td>{cell_text}</td>'
            row_html += "<td></td><td></td><td>&#10003;</td><td></td><td></td>"; row_html += "</tr>"; rows_html_list.append(row_html)
        table_rows_content = "\n".join(rows_html_list)
        final_html = template_content.replace("{{name}}", name).replace("{{designation}}", designation).replace("{{month_year}}", month_year).replace("{{table_rows}}", table_rows_content)
        try:
            with open(save_path, 'w', encoding='utf-8') as f: f.write(final_html)
            QMessageBox.information(self, "Success", f"Report saved to:\n{save_path}"); QDesktopServices.openUrl(QUrl.fromLocalFile(save_path))
        except Exception as e: QMessageBox.critical(self, "Error", f"Failed to save or open report: {e}")

    def _update_button_states(self):
        selected_indexes = self.table.selectedIndexes()
        selected_rows = set(index.row() for index in selected_indexes)
        num_selected_rows = len(selected_rows)

        self.set_progress_button.setEnabled(num_selected_rows == 1)
        self.merge_button.setEnabled(num_selected_rows > 1)
        self.unassign_qa83_button.setEnabled(num_selected_rows == 1)
        self.override_desc_button.setEnabled(num_selected_rows == 1)

        is_merged = False
        if num_selected_rows == 1:
            row = list(selected_rows)[0]
            desc_item = self.table.item(row, 2)
            if desc_item:
                is_merged = desc_item.data(Qt.ItemDataRole.UserRole + 1) or False
        self.edit_merged_task_button.setEnabled(is_merged)

    def _unassign_qa83_tag(self):
        selected_rows = list(set(index.row() for index in self.table.selectedIndexes()))
        if len(selected_rows) != 1: return
        
        row = selected_rows[0]
        group_key = self.table.item(row, 2).data(Qt.ItemDataRole.UserRole)
        if not group_key: return

        proj_code, html_desc = group_key
        reply = QMessageBox.question(self, "Confirm Unassign", 
            f"Are you sure you want to remove the 'QA83' tag from all tasks in this group?\n\n<b>Project:</b> {proj_code}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            month_year_str = self.view_date.strftime('%Y-%m')
            task_ids = self.db.get_task_ids_for_group(month_year_str, proj_code, html_desc)
            
            for task_id in task_ids:
                task = self.db.get_task_by_id(task_id)
                if task and task[6]:
                    categories = task[6].split(',')
                    new_categories = [cat.strip() for cat in categories if cat.strip().upper() != "QA83"]
                    self.db.update_task_categories(task_id, ",".join(new_categories))
            
            QMessageBox.information(self, "Success", "QA83 tag unassigned successfully.")
            self.update_qa83_view()

    def _edit_merged_task(self):
        selected_rows = list(set(index.row() for index in self.table.selectedIndexes()))
        if len(selected_rows) != 1: return
        
        row = selected_rows[0]
        desc_item = self.table.item(row, 2)
        if not desc_item or not desc_item.data(Qt.ItemDataRole.UserRole + 1):
            QMessageBox.warning(self, "Action Not Applicable", "This task is not part of a merged group.")
            return

        master_id = desc_item.data(Qt.ItemDataRole.UserRole + 2)
        if not master_id: return

        dialog = EditMergedTaskDialog(master_id, self.db, self)
        if dialog.exec():
            new_desc, ids_to_unmerge, total_children = dialog.get_changes()
            
            # Check if all children are being unmerged.
            if total_children > 0 and len(ids_to_unmerge) == total_children:
                # All children are unmerged, so dissolve the group.
                # This includes the master task itself.
                self.db.unmerge_specific_tasks(ids_to_unmerge + [master_id])
            else:
                # Otherwise, just update the description and unmerge selected tasks.
                self.db.set_merged_description(master_id, new_desc)

            if ids_to_unmerge:
                self.db.unmerge_specific_tasks(ids_to_unmerge)

            QMessageBox.information(self, "Success", "Merged task updated successfully.")
            self.update_qa83_view()
    
    def _add_months(self, source_date, months):
        month = source_date.month - 1 + months; year = source_date.year + month // 12; month = month % 12 + 1; return source_date.replace(year=year, month=month, day=1)
    
    def _go_to_previous_month(self): self.view_date = self._add_months(self.view_date, -1); self.update_qa83_view()
    def _go_to_next_month(self): self.view_date = self._add_months(self.view_date, 1); self.update_qa83_view()
    
    def _show_calendar_picker(self, event):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Date")
        cal_layout = QVBoxLayout(dialog)
        calendar = QCalendarWidget()
        calendar.setSelectedDate(QDate(self.view_date))
        
        def on_date_selected():
            self.view_date = calendar.selectedDate().toPython()
            self.update_qa83_view()
            dialog.accept()
            
        calendar.selectionChanged.connect(on_date_selected)
        cal_layout.addWidget(calendar)
        dialog.exec()
    
    def _get_month_weeks_info(self, year, month):
        month_calendar = calendar.monthcalendar(year, month); day_to_week_map, headers = {}, []
        chrono_week_idx = 0; week_number_suffix = {1: 'st', 2: 'nd', 3: 'rd'}
        for week in month_calendar:
            week_days = [day for day in week if day != 0]
            if not week_days: continue
            week_num = chrono_week_idx + 1; suffix = week_number_suffix.get(week_num, 'th')
            start_date, end_date = datetime(year, month, week_days[0]), datetime(year, month, week_days[-1])
            header_text = f"{week_num}{suffix} Week\n({start_date.strftime('%d/%m')} -\n{end_date.strftime('%d/%m')})"
            headers.append(header_text)
            for day in week_days: day_to_week_map[day] = chrono_week_idx
            chrono_week_idx += 1
        return headers, day_to_week_map, len(headers)
    
    def _set_task_progress(self):
        selected_rows = list(set(index.row() for index in self.table.selectedIndexes()));
        if len(selected_rows) != 1: return
        row = selected_rows[0]; group_key = self.table.item(row, 2).data(Qt.ItemDataRole.UserRole)
        if not group_key: return
        proj_code, html_desc = group_key; doc = QTextDocument(); doc.setHtml(html_desc); month_year_str = self.view_date.strftime('%Y-%m')
        
        current_start, current_final = self.db.get_qa83_progress(month_year_str, proj_code, html_desc)
        current_start_progress = current_start or "0"
        current_final_progress = current_final or "100"

        dialog = ProgressInputDialog(proj_code, doc.toPlainText(), current_start_progress, current_final_progress, self)
        
        if dialog.exec():
            new_start, new_final = dialog.get_values()
            self.db.set_qa83_progress(month_year_str, proj_code, html_desc, new_start, new_final)
            self.update_qa83_view()
    
    def _merge_selected_tasks(self):
        selected_rows = sorted(list(set(index.row() for index in self.table.selectedIndexes())));
        if len(selected_rows) < 2: return
        task_groups_to_merge = [];
        for row in selected_rows:
            group_key = self.table.item(row, 2).data(Qt.ItemDataRole.UserRole)
            if group_key: task_groups_to_merge.append(group_key)
        dialog = MergeTasksDialog(task_groups_to_merge, self)
        if dialog.exec():
            master_group, merged_desc = dialog.get_selection(); month_year_str = self.view_date.strftime('%Y-%m'); all_task_ids = []
            for proj_code, html_desc in task_groups_to_merge: all_task_ids.extend(self.db.get_task_ids_for_group(month_year_str, proj_code, html_desc))
            master_task_ids = self.db.get_task_ids_for_group(month_year_str, master_group[0], master_group[1])
            if not master_task_ids: QMessageBox.critical(self, "Error", "Could not find master task."); return
            the_one_master_id = master_task_ids[0]; self.db.set_master_for_tasks(all_task_ids, the_one_master_id)
            if merged_desc: self.db.set_merged_description(the_one_master_id, merged_desc)
            QMessageBox.information(self, "Success", f"{len(all_task_ids)} task entries merged."); self.update_qa83_view()
    
    def update_qa83_view(self):
        self.table.clearContents(); self.table.setRowCount(0); self.month_label.setText(self.view_date.strftime('%B %Y')); month_year_str = self.view_date.strftime('%Y-%m')
        week_headers, day_to_week_map, num_weeks = self._get_month_weeks_info(self.view_date.year, self.view_date.month)
        headers = ["Project Code", "Project Title", "Description"] + week_headers
        self.table.setColumnCount(len(headers)); self.table.setHorizontalHeaderLabels(headers); header = self.table.horizontalHeader()
        for i in range(3, self.table.columnCount()): header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setFixedHeight(header.sizeHint().height()); header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        all_tasks = self.db.get_tasks_for_month_with_master_info(month_year_str); qa83_categories = set(self.qa83_config.get("qa83_categories", [])); qa83_tasks = [task for task in all_tasks if qa83_categories.intersection(set(task[6].split(',')))]; task_groups = {}
        for task in qa83_tasks:
            group_id = task[8] if task[8] else task[0]; task_start_dt = datetime.combine(datetime.strptime(task[1], '%Y-%m-%d'), time.fromisoformat(task[2]))
            if group_id not in task_groups:
                master_task = next((t for t in all_tasks if t[0] == group_id), None)
                if not master_task: continue
                
                # Correctly determine the description: overridden on master, or original.
                # If it's a merged group, master_task[11] has the merged description.
                # If it's a single task, we need to check its own overridden description from the database.
                task_groups[group_id] = { "proj_code": master_task[4], "description": self.db.get_task_by_id(group_id)[9] or master_task[5], "original_key": (master_task[4], master_task[5]), "tasks": [], "earliest_start_dt": task_start_dt }
            task_groups[group_id]["tasks"].append(task); task_groups[group_id]["earliest_start_dt"] = min(task_groups[group_id]["earliest_start_dt"], task_start_dt)
        sorted_groups = sorted(list(task_groups.values()), key=lambda g: (g['proj_code'], g['earliest_start_dt'])); projects_data = defaultdict(list)
        for group in sorted_groups: projects_data[group['proj_code']].append(group)
        self.table.setRowCount(len(sorted_groups)); current_row = 0
        
        group_id_map = {v['original_key']: k for k, v in task_groups.items()}

        for proj_code, groups_in_project in projects_data.items():
            start_row_for_span = current_row
            title = self.db.get_project_title(proj_code) or ""
            
            proj_code_item = QTableWidgetItem(proj_code)
            proj_code_item.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(current_row, 0, proj_code_item)

            title_item = QTableWidgetItem(title)
            title_item.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(current_row, 1, title_item)
            for group in groups_in_project:
                desc_item = QTableWidgetItem()
                
                desc_item.setData(Qt.ItemDataRole.UserRole, group["original_key"])
                is_group_merged = any(task[8] is not None for task in group["tasks"])
                desc_item.setData(Qt.ItemDataRole.UserRole + 1, is_group_merged)
                group_id = group_id_map.get(group["original_key"])
                desc_item.setData(Qt.ItemDataRole.UserRole + 2, group_id)

                self.table.setItem(current_row, 2, desc_item)
                desc_label = QLabel(group["description"])
                desc_label.setTextFormat(Qt.TextFormat.RichText)
                desc_label.setWordWrap(True)
                desc_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                self.table.setCellWidget(current_row, 2, desc_label)
                weekly_hours = [0.0] * num_weeks; total_hours = 0.0
                for task in group["tasks"]:
                    day = datetime.strptime(task[1], '%Y-%m-%d').day; week_idx = day_to_week_map.get(day)
                    if week_idx is not None:
                        duration = (datetime.combine(datetime.min, time.fromisoformat(task[3])) - datetime.combine(datetime.min, time.fromisoformat(task[2]))).total_seconds() / 3600; weekly_hours[week_idx] += duration; total_hours += duration
                
                orig_proj, orig_desc = group["original_key"]
                start_progress_str, final_progress_str = self.db.get_qa83_progress(month_year_str, orig_proj, orig_desc)
                start_progress_str = start_progress_str or "0"
                final_progress_str = final_progress_str or "100"

                col_offset = 3
                if final_progress_str == "-":
                    for i, hours in enumerate(weekly_hours):
                        if hours > 0.005: item = QTableWidgetItem("-"); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(current_row, i + col_offset, item)
                else:
                    try:
                        start_progress = float(start_progress_str)
                        final_progress = float(final_progress_str)
                        total_progress_gain = final_progress - start_progress
                        cumulative_progress = start_progress
                        
                        for i, hours in enumerate(weekly_hours):
                            progress_gain = (hours / total_hours) * total_progress_gain if total_hours > 0 else 0
                            cumulative_progress += progress_gain
                            if hours > 0.005: 
                                item = QTableWidgetItem(f"{cumulative_progress:.0f}%")
                                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                                self.table.setItem(current_row, i + col_offset, item)
                    except (ValueError, TypeError): pass
                current_row += 1
            span_size = len(groups_in_project)
            if span_size > 1: self.table.setSpan(start_row_for_span, 0, span_size, 1); self.table.setSpan(start_row_for_span, 1, span_size, 1)
        self.table.resizeRowsToContents()