#!/usr/bin/env python3
import os.path
import re
import sys
from dicteditor.utils import sum
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, QPushButton, QStyledItemDelegate, QLineEdit, QLabel, \
    QHeaderView, QMenu, QFileDialog, QErrorMessage, QMessageBox

import json

import yaml
import easyconfig
import dicteditor.resources
from easyconfig.EasyConfig import EasyConfig


def get_elem_from_text(text):
    try:
        value = int(text)
    except ValueError:
        try:
            value = float(text)
        except ValueError:
            value = text
    return value


class Item(QTreeWidgetItem):
    color_int = QtCore.Qt.darkGreen
    color_float = QtCore.Qt.cyan
    color_string = QtCore.Qt.black
    color_dict = QtCore.Qt.red
    color_list = QtCore.Qt.darkGreen

    def __init__(self, parent, data):
        super().__init__(parent, data)
        self.item_flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable
        self.setFlags(self.item_flags)
        self.key_type = type(self.get_key())
        self.value_type = type(self.get_value())
        self.update_type()
        self.widgets = {}

    def readonly(self, columns):
        for column in columns:
            label = QLabel(self.data(column, 0))
            self.treeWidget().setItemWidget(self, column, label)
            label.setStyleSheet("color:" + self.foreground(column).color().name())
            # Necessary to make resizeColumnsToContents() work
            self.setData(column, 0, " " * len(self.data(column, 0)))
            self.widgets[column] = label

    def get_key(self):
        return get_elem_from_text(self.text(0))

    def update_type(self):
        self.key_type = type(self.get_key())
        self.value_type = type(self.get_value())

    def get_value(self):
        return get_elem_from_text(self.text(1))

    def setText(self, column: int, atext: str) -> None:
        if self.widgets.get(column) is not None:
            self.widgets[column].setText(atext)
            super(Item, self).setText(column, " " * len(atext))
        else:
            super().setText(column, atext)

    def apply_color(self):
        pass

    def set_color(self, check_type, column=1):
        if check_type == str:
            self.setForeground(column, self.color_string)
        elif check_type == int:
            self.setForeground(column, self.color_int)
        elif check_type == float:
            self.setForeground(column, self.color_float)
        else:
            self.setForeground(column, QtCore.Qt.darkMagenta)


class DictRoot(Item):
    def __init__(self, parent):
        super().__init__(parent, ["{dict}"])
        self.setForeground(0, self.color_dict)
        self.readonly([0])


class ListRoot(Item):
    def __init__(self, parent):
        super().__init__(parent, ["[list]"])
        self.setForeground(0, self.color_list)
        self.readonly([0])


class DictEntryDict(Item):
    def __init__(self, parent, key):
        super().__init__(parent, [str(key), "{dict}"])
        self.setForeground(1, self.color_dict)
        self.readonly([1])
        self.apply_color()

    def apply_color(self):
        self.set_color(self.key_type, 0)


class DictEntryList(Item):
    def __init__(self, parent, key):
        super().__init__(parent, [str(key), "[list]"])
        self.setForeground(1, self.color_list)
        self.readonly([1])
        self.apply_color()

    def apply_color(self):
        self.set_color(self.key_type, 0)


class DictEntryValue(Item):
    def __init__(self, parent, key, value):
        super().__init__(parent, [str(key), str(value)])
        self.apply_color()

    def apply_color(self):
        self.set_color(self.key_type, 0)
        self.set_color(self.value_type, 1)


class ListEntry(Item):
    pass


class ListEntryList(ListEntry):
    def __init__(self, parent, key):
        super().__init__(parent, ["[" + str(key) + "]", "[list]"])
        self.setForeground(0, QtCore.Qt.black)
        self.readonly([0, 1])
        self.apply_color()

    def apply_color(self):
        self.set_color(self.value_type, 1)


class ListEntryValue(ListEntry):
    def __init__(self, parent, key, value):
        super().__init__(parent, ["[" + str(key) + "]", str(value)])
        self.setForeground(0, QtCore.Qt.black)
        self.readonly([0])
        self.apply_color()

    def apply_color(self):
        self.set_color(self.value_type, 1)


class ListEntryDict(ListEntry):
    def __init__(self, parent, key):
        super().__init__(parent, ["[" + str(key) + "]", "{dict}"])
        self.setForeground(0, QtCore.Qt.black)
        self.setForeground(1, QtCore.Qt.red)
        self.readonly([0, 1])


class DictTreeWidget(QTreeWidget):
    def __init__(self):
        super().__init__()
        font = QFont("Courier New", 12)  # Create a QFont object specifying the monospace font family and size
        self.setFont(font)
        self.itemExpanded.connect(self.resize_column)
        self.setColumnCount(2)
        # self.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)

    def resize_column(self):
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)

    def contextMenuEvent(self, a0: QtGui.QContextMenuEvent) -> None:
        super().contextMenuEvent(a0)
        index = self.indexAt(a0.pos())
        item = self.itemFromIndex(index)

        menu = QMenu()
        del_entry = menu.addAction("Delete")

        add_dict_entry, add_list_entry = None, None

        if type(item) in [ListEntryDict, DictEntryDict, DictRoot]:
            add_dict_entry = menu.addAction("Add Dict Entry")

        elif type(item) in [ListEntryList, DictEntryList, ListRoot]:
            add_list_entry = menu.addAction("Add List Entry")

        res = menu.exec(a0.globalPos())
        if res is None:
            pass
        elif res == add_dict_entry:
            new_item = DictEntryValue(item, "new_key", "new_value")
            item.addChild(new_item)
        elif res == del_entry:
            parent = item.parent()
            parent.removeChild(item)
            if isinstance(item, ListEntry):
                for i in range(parent.childCount()):
                    list_item = parent.child(i)
                    list_item.setText(0, "[" + str(i) + "]")
            del item

        elif res == add_list_entry:
            # parent = item.parent()
            new_item = ListEntryValue(item, item.childCount(), "new_value")
            item.addChild(new_item)

    def populate_tree(self, value, parent=None, key=None):
        if parent is None:
            if type(value) == dict:
                parent = DictRoot(self.invisibleRootItem())
                self.addTopLevelItem(parent)
                self.invisibleRootItem().addChild(parent)
                for key, value in value.items():
                    self.populate_tree(value, parent, key)
            elif type(value) == list:
                parent = ListRoot(self.invisibleRootItem())
                self.addTopLevelItem(parent)
                self.invisibleRootItem().addChild(parent)
                for i, elem in enumerate(value):
                    self.populate_tree(elem, parent, i)
            return
        elif type(parent) in [ListRoot, DictEntryList, ListEntryList]:
            if type(value) == dict:
                item = ListEntryDict(parent, key)
                for key, value in value.items():
                    self.populate_tree(value, item, key)
                parent.addChild(item)
            elif type(value) == list:
                item = ListEntryList(parent, key)
                for i, elem in enumerate(value):
                    self.populate_tree(elem, item, i)
                parent.addChild(item)
            else:
                item = ListEntryValue(parent, key, value)
                parent.addChild(item)
        elif type(parent) in [DictRoot, DictEntryDict, ListEntryDict]:
            if type(value) == dict:
                item = DictEntryDict(parent, key)
                for key, value in value.items():
                    self.populate_tree(value, item, key)
                parent.addChild(item)
            elif type(value) == list:
                item = DictEntryList(parent, key)
                for i, elem in enumerate(value):
                    self.populate_tree(elem, item, i)
                parent.addChild(item)
            else:
                item = DictEntryValue(parent, key, value)
                parent.addChild(item)

    def traverse_tree(self, item, output=None):
        if type(item) == DictRoot:
            output = {}
            for i in range(item.childCount()):
                self.traverse_tree(item.child(i), output)
        elif type(item) == ListRoot:
            output = []
            for i in range(item.childCount()):
                self.traverse_tree(item.child(i), output)
        elif type(item) == DictEntryValue:
            output[item.get_key()] = item.get_value()
        elif type(item) == DictEntryList:
            output[item.get_key()] = []
            for i in range(item.childCount()):
                self.traverse_tree(item.child(i), output[item.get_key()])
        elif type(item) == DictEntryDict:
            output[item.get_key()] = {}
            for i in range(item.childCount()):
                self.traverse_tree(item.child(i), output[item.get_key()])
        elif type(item) == ListEntryValue:
            output.append(item.get_value())
        elif type(item) == ListEntryList:
            output.append([])
            for i in range(item.childCount()):
                self.traverse_tree(item.child(i), output[-1])
        elif type(item) == ListEntryDict:
            output.append({})
            for i in range(item.childCount()):
                self.traverse_tree(item.child(i), output[-1])

        return output

    def traverse_tree_2(self, item, output=None):
        if output is None:
            output = {} if isinstance(item, DictRoot) else []  # Initialize output if not provided

        if isinstance(item, (DictRoot, ListRoot)):
            for i in range(item.childCount()):
                self.traverse_tree_2(item.child(i), output)
        elif isinstance(item, (DictEntryValue, ListEntryValue)):
            if isinstance(item, DictEntryValue):
                output[item.get_key()] = item.get_value()
            else:
                output.append(item.get_value())
        elif isinstance(item, (DictEntryList, ListEntryList)):
            sub_output = []
            for i in range(item.childCount()):
                self.traverse_tree_2(item.child(i), sub_output)
            if isinstance(item, DictEntryList):
                output[item.get_key()] = sub_output
            else:
                output.append(sub_output)
        elif isinstance(item, (DictEntryDict, ListEntryDict)):
            sub_output = {}
            for i in range(item.childCount()):
                self.traverse_tree_2(item.child(i), sub_output)
            if isinstance(item, DictEntryDict):
                output[item.get_key()] = sub_output
            else:
                output.append(sub_output)

        return output


class DictEditorWindow(QMainWindow):
    colors = ["black", "red", "green", "blue", "cyan", "magenta", "yellow", "gray"]
    qcolors = [Qt.black, Qt.red, Qt.darkGreen, Qt.blue, Qt.cyan, Qt.magenta, Qt.yellow, Qt.gray]

    def __init__(self):
        super().__init__()

        config_dir = os.path.join(os.path.expanduser('~'), '.config', 'dict-editor')
        self.config_file = config_dir + os.sep + "config.yaml"
        os.makedirs(config_dir, exist_ok=True)

        self.config = EasyConfig()
        general = self.config.root().addSubSection("General")
        open_last = general.addCheckbox("open_last", pretty="Open last file", default=True)

        colors = self.config.root().addSubSection("Colors")
        self.color_string = colors.addCombobox("string", pretty="String", items=self.colors, default=3)
        self.color_int = colors.addCombobox("int", pretty="Int", items=self.colors, default=2)
        self.color_float = colors.addCombobox("float", pretty="Float", items=self.colors, default=4)
        self.color_dict = colors.addCombobox("dict", pretty="Dict", items=self.colors, default=1)
        self.color_list = colors.addCombobox("list", pretty="List", items=self.colors, default=5)
        private = self.config.root().addHidden("private")
        self.filename = private.addString("filename")
        self.expanded = private.addString("expanded")
        self.pose = private.addList("pose")
        self.config.load(self.config_file)

        self.update_colors()

        self.setWindowTitle("Dictionary Editor")
        pose = self.pose.get_value()
        if pose is not None:
            self.setGeometry(pose[0], pose[1], pose[2], pose[3])

        file = self.menuBar().addMenu("File")
        file.addAction("Open", self.open_file)
        file.addAction("Save", self.save)
        file.addAction("Save as", self.save_as)
        edit = self.menuBar().addMenu("Edit")
        edit.addAction("Preferences", self.edit_preferences)

        tb = self.addToolBar("File")
        tb.addAction(QIcon(":/icons/open.png"), "Open", self.open_file)
        tb.addAction(QIcon(":/icons/save.png"), "Save", self.save)
        tb.addSeparator()
        tb.addAction(QIcon(":/icons/expand.png"), "Expand all", self.expand_all)
        tb.addSeparator()
        tb.addAction(QIcon(":/icons/refresh.png"), "Refresh", self.refresh)

        self.tree_widget = DictTreeWidget()
        self.tree_widget.setHeaderLabels(["Key", "Value"])
        helper = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.tree_widget)
        helper.setLayout(layout)
        self.setCentralWidget(helper)
        self.setWindowTitle("Dictionary Editor")
        self.show()

        self.current_filename = self.filename.get_value()

        if len(sys.argv) > 1:
            self.current_filename = sys.argv[1]
            self.open_file(self.current_filename)

        elif self.current_filename is not None and os.path.exists(self.current_filename) and open_last.get_value() is True:
            self.open_file(self.current_filename)
            expanded = self.expanded.get_value()
            if expanded is not None:
                self.set_expanded_recursive([int(x) for x in expanded])

        self.tree_widget.itemChanged.connect(self.item_changed)

    def expand_all(self):
        self.tree_widget.expandAll()
        self.tree_widget.resizeColumnToContents(0)
        self.tree_widget.resizeColumnToContents(1)

    def update_colors(self):
        Item.color_int = self.qcolors[self.color_int.get_value()]
        Item.color_float = self.qcolors[self.color_float.get_value()]
        Item.color_string = self.qcolors[self.color_string.get_value()]
        Item.color_dict = self.qcolors[self.color_dict.get_value()]
        Item.color_list = self.qcolors[self.color_list.get_value()]

    def edit_preferences(self):
        if self.config.exec():
            self.config.save(self.config_file)
            self.update_colors()
            expanded = self.get_expanded_recursive()
            data = self.tree_widget.traverse_tree(self.tree_widget.invisibleRootItem().child(0))
            self.populate(data)
            self.set_expanded_recursive(expanded)

    def item_changed(self, item, column):
        item.update_type()
        item.apply_color()

    def save(self, filename=None):
        self.current_filename = filename if filename else self.current_filename
        if self.current_filename:
            data = self.tree_widget.traverse_tree(self.tree_widget.invisibleRootItem().child(0))
            with open(self.current_filename, "w") as f:
                if self.current_filename.endswith(".json"):
                    json.dump(data, f)
                elif self.current_filename.endswith(".yaml"):
                    yaml.dump(data, f)
            self.setWindowTitle("Dictionary Editor - " + self.current_filename)

    def save_as(self):
        options = QFileDialog.Options()
        filename, ext = QFileDialog.getSaveFileName(self, "Save File", "", "YAML files (*.yaml) ;; JSON Files (*.json)", options=options)
        if filename:
            print("hijhlkj", ext)
            ext = re.search(r'\(\*(\.[a-zA-Z0-9]+)\)', ext).group(1)
            if not filename.endswith(ext):
                filename += ext
            self.save(filename)

    def show_error_message(self, message):
        msg = QMessageBox(parent=self)
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Error")
        msg.exec_()

    def open_file(self, filename=None):
        directory = None
        if filename is None:
            filename, _ = QFileDialog.getOpenFileName(self, "Open File", directory, "YAML or JSON Files (*.json *.yaml)")

        if filename:
            if not os.path.exists(filename):
                self.show_error_message("File does {} not exist".format(filename))
                return

            if filename.endswith(".json"):
                with open(filename, "r") as f:
                    data = json.load(f)
            elif filename.endswith(".yaml"):
                with open(filename, "r") as f:
                    data = yaml.load(f, Loader=yaml.FullLoader)
            else:
                self.show_error_message("File must be a YAML or JSON file")
                return

            self.current_filename = filename
            self.setWindowTitle("Dictionary Editor - " + filename)
            self.populate(data)

    def populate(self, data):
        try:
            self.tree_widget.clear()
            self.tree_widget.populate_tree(data, None)
            self.tree_widget.resizeColumnToContents(0)
            self.tree_widget.resizeColumnToContents(1)
        except Exception as e:
            self.show_error_message("Error populating tree" + str(e))

    def get_expanded_recursive(self):
        expanded = []

        def traverse(item):
            expanded.append(item.isExpanded())
            for i in range(item.childCount()):
                traverse(item.child(i))

        traverse(self.tree_widget.invisibleRootItem())
        return expanded

    def set_expanded_recursive(self, expanded):

        def traverse(item):
            item.setExpanded(expanded.pop(0))
            for i in range(item.childCount()):
                traverse(item.child(i))

        traverse(self.tree_widget.invisibleRootItem())

    def refresh(self):
        v = self.get_expanded_recursive()
        if self.current_filename:
            self.open_file(self.current_filename)
            self.set_expanded_recursive(v)

    def closeEvent(self, a0):
        print("akkkkkkkkkkk", self.current_filename)
        v = self.get_expanded_recursive()
        expanded = ""
        for e in v:
            expanded += "1" if e else "0"

        geometry = [self.geometry().x(), self.geometry().y(), self.geometry().width(), self.geometry().height()]
        self.pose.set_value(geometry)
        self.filename.set_value(self.current_filename)
        self.expanded.set_value(expanded)
        self.config.save(self.config_file)

        super().closeEvent(a0)


def main():
    app = QApplication(sys.argv)
    window = DictEditorWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
