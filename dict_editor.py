import os.path
import re
import sys

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, QPushButton, QStyledItemDelegate, QLineEdit, QLabel, \
    QHeaderView, QMenu, QFileDialog

import json

import yaml
class Item(QTreeWidgetItem):
    def __init__(self, parent, data):
        super().__init__(parent, data)
        self.item_flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable
        self.setFlags(self.item_flags)
        self.key_type = str
        self.value_type = str
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
        try:
            key = self.key_type(self.text(0))
        except ValueError:
            key = self.text(0)
        return key

    def get_value(self):
        try:
            value = self.value_type(self.text(1))
        except ValueError:
            value = self.text(1)
        return value

    def setText(self, column: int, atext: str) -> None:
        if self.widgets.get(column) is not None:
            self.widgets[column].setText(atext)
            super(Item, self).setText(column, " " * len(atext))
        else:
            super().setText(column, atext)


class DictRoot(Item):
    def __init__(self, parent):
        super().__init__(parent, ["{dict}"])
        self.setForeground(0, QtCore.Qt.red)
        self.readonly([0])


class ListRoot(Item):
    def __init__(self, parent):
        super().__init__(parent, ["[list]"])
        self.setForeground(0, QtCore.Qt.magenta)
        self.readonly([0])


class DictEntryDict(Item):
    def __init__(self, parent, key):
        super().__init__(parent, [str(key), "{dict}"])
        self.key_type = type(key)
        self.setForeground(0, QtCore.Qt.red)
        self.setForeground(1, QtCore.Qt.red)
        self.readonly([1])


class DictEntryList(Item):
    def __init__(self, parent, key):
        super().__init__(parent, [str(key), "[list]"])
        self.key_type = type(key)
        self.setForeground(0, QtCore.Qt.darkGreen)
        self.setForeground(1, QtCore.Qt.darkGreen)
        self.readonly([1])


class DictEntryValue(Item):
    def __init__(self, parent, key, value):
        super().__init__(parent, [str(key), str(value)])
        self.key_type = type(key)
        self.value_type = type(value)
        self.setForeground(0, QtCore.Qt.magenta)
        self.setForeground(1, QtCore.Qt.blue)


class ListEntry(Item):
    pass


class ListEntryList(ListEntry):
    def __init__(self, parent, key):
        super().__init__(parent, ["[" + str(key) + "]", "[list]"])
        self.setForeground(0, QtCore.Qt.black)
        self.setForeground(1, QtCore.Qt.darkGreen)
        self.readonly([0, 1])


class ListEntryValue(ListEntry):
    def __init__(self, parent, key, value):
        super().__init__(parent, ["[" + str(key) + "]", str(value)])
        self.value_type = type(value)
        self.setForeground(0, QtCore.Qt.black)
        self.setForeground(1, QtCore.Qt.blue)
        self.readonly([0])


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
        print("contextMenuEvent")
        super().contextMenuEvent(a0)
        index = self.indexAt(a0.pos())
        item = self.itemFromIndex(index)
        print(item, type(item))

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
    def __init__(self):
        super().__init__()
        self.filename = None

        self.setWindowTitle("Dictionary Editor")
        self.setGeometry(100, 100, 600, 400)
        file = self.menuBar().addMenu("File")
        file.addAction("Open", self.open_file)
        file.addAction("Save", self.save)
        file.addAction("Save as", self.save_as)

        self.config = {}
        try:
            with open("config.yaml", "r") as f:
                self.config = yaml.load(f, Loader=yaml.FullLoader)
        except FileNotFoundError:
            pass


        tb = self.addToolBar("File")
        tb.addAction(QIcon("icons/open.png"), "Open", self.open_file)
        tb.addAction(QIcon("icons/save.png"), "Save", self.save)
        tb.addAction(QIcon("icons/refresh.png"), "Refresh",  self.refresh )

        self.tree_widget = DictTreeWidget()
        self.tree_widget.setHeaderLabels(["Key", "Value"])
        '''
        self.tree_widget.populate_tree({
            1:1,
            2:2,
            3:3,
            4:4,
            5:{11: 2,
               22: 1,
               888: {1: 2, 5: 6},
               37: [
                 33,
                 44,
                 55,
                 {666: 777, 888: 999},
                 [43, 45,45, [9, 0, 0],{1: 90, 2: 91}]
                ],
             44: {55: 66, 77: 88}
             }
        },
            None)
        self.tree_widget.resizeColumnToContents(0)
        self.out = None
        out = self.tree_widget.traverse_tree(self.tree_widget.invisibleRootItem().child(0))
        print("Output", out)
        self.tree_widget.setHeaderLabels(["Name", "Value"])'''
        helper = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.tree_widget)
        helper.setLayout(layout)
        self.setCentralWidget(helper)
        self.setWindowTitle("Dictionary Editor")
        try:
            with open("dict-editor.yaml", "r") as f:
                self.config = yaml.load(f, Loader=yaml.FullLoader)
                self.open_file(self.config["filename"])
                self.set_expanded_recursive([int(x) for x in self.config["expanded"]])
                x = self.config.get("geometry", [0,0, 100,200])
                self.setGeometry(x[0], x[1], x[2], x[3])
        except FileNotFoundError:
            pass




    #def print_data(self):
    #    print(self.tree_widget.traverse_tree(self.tree_widget.invisibleRootItem().child(0)))
    #    print(self.tree_widget.traverse_tree_2(self.tree_widget.invisibleRootItem().child(0)))

    def save(self, filename=None):
        self.filename = filename if filename else self.filename
        if self.filename:
            data = self.tree_widget.traverse_tree(self.tree_widget.invisibleRootItem().child(0))
            with open(self.filename, "w") as f:
                if self.filename.endswith(".json"):
                    json.dump(data, f)
                elif self.filename.endswith(".yaml"):
                    yaml.dump(data, f)
            self.setWindowTitle("Dictionary Editor - " + self.filename)
    def save_as(self):
        filename, ext = QFileDialog.getSaveFileName(self, "Save File", "", "JSON Files (*.json);;YAML Files (*.yaml)")
        if filename:
            ext = re.search(r'\(\*(\.[a-zA-Z0-9]+)\)', ext).group(1)
            if not filename.endswith(ext):
                filename += ext
            self.save(filename)
    def open_file(self, filename=None):
        directory = self.config.get("directory", "")
        if filename is None:
            filename, _ = QFileDialog.getOpenFileName(self, "Open File", directory, "JSON Files (*.json);;YAML Files (*.yaml)")

        if filename:
            if filename.endswith(".json"):
                with open(filename, "r") as f:
                    data = json.load(f)
            elif filename.endswith(".yaml"):
                with open(filename, "r") as f:
                    data = yaml.load(f, Loader=yaml.FullLoader)

            directory = os.path.dirname(filename)
            self.config["directory"] = directory
            with open("config.yaml", "w") as f:
                yaml.dump(self.config, f)
            self.filename = filename
            self.tree_widget.clear()
            self.tree_widget.populate_tree(data, None)
            self.tree_widget.resizeColumnToContents(0)
            self.tree_widget.resizeColumnToContents(1)
            self.setWindowTitle("Dictionary Editor - " + filename)

    def get_expanded_recursive(self):
        expanded = []
        def traverse(item):
            expanded.append(item.isExpanded())
            for i in range(item.childCount()):
                traverse(item.child(i))

        traverse(self.tree_widget.invisibleRootItem())
        return expanded

    def set_expanded_recursive(self, expanded):
        print(expanded)
        def traverse(item):
            item.setExpanded(expanded.pop(0))
            for i in range(item.childCount()):
                traverse(item.child(i))

        traverse(self.tree_widget.invisibleRootItem())


    def refresh(self):
        v = self.get_expanded_recursive()
        if self.filename:
            self.open_file(self.filename)
            self.set_expanded_recursive(v)

    def closeEvent(self, a0):
        if self.filename:
            with open("dict-editor.yaml", "w") as f:
                v = self.get_expanded_recursive()
                expanded = ""
                for e in v:
                    expanded += "1" if e else "0"

                geometry = [self.geometry().x(), self.geometry().y(), self.geometry().width(), self.geometry().height()]
                yaml.dump({"filename": self.filename, "expanded": expanded, "geometry": geometry}, f)


        super().closeEvent(a0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DictEditorWindow()
    window.show()
    sys.exit(app.exec_())
