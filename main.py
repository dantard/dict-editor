#!/bin/env python
import sys

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem


class Item(QTreeWidgetItem):
    def __init__(self, parent, data):
        super().__init__(parent, data)
        self.data = data
        self.item_flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable
        self.setFlags(self.item_flags)


class DictTreeItem(Item):
    def __init__(self, parent, data):
        super().__init__(parent, data)
        self.setForeground(0, QtCore.Qt.magenta)


class ListTreeItem(Item):
    def __init__(self, parent, data):
        super().__init__(parent, data)
        self.setForeground(0, QtCore.Qt.red)


class DictionaryValueItem(Item):
    def __init__(self, parent, key, value):
        super().__init__(parent, [str(key), str(value)])
        self.key = key
        self.value = value
        self.setForeground(0, QtCore.Qt.blue)


class DictionaryListItem(Item):
    def __init__(self, parent, key):
        super().__init__(parent, [str(key), "[]"])
        self.key = key
        self.setForeground(0, QtCore.Qt.darkRed)


class DictionaryDictItem(Item):
    def __init__(self, parent, key):
        super().__init__(parent, [str(key), "{}"])
        self.key = key
        self.setForeground(0, QtCore.Qt.darkBlue)

class DictionaryEntry(Item):
    def __init__(self, parent, key, value):
        super().__init__(parent, [str(key), str(value)])
        self.key = key
        self.value = value
        self.setForeground(0, QtCore.Qt.darkBlue)

class ValueItem(Item):
    def __init__(self, parent, value, key=""):
        super().__init__(parent, [str(key), str(value)])
        self.value = value
        self.setForeground(1, QtCore.Qt.darkGreen)


class DictTreeWidget(QTreeWidget):
    def __init__(self):
        super().__init__()

        self.setHeaderLabels(["Key", "Value"])
        # self.populate_tree(dictionary)

    def populate_tree(self, value, parent=None, key=None):
        if parent is None:
            parent = DictTreeItem(self.invisibleRootItem(), [])
            self.addTopLevelItem(parent)
            self.invisibleRootItem().addChild(parent)
            for key, value in value.items():
                self.populate_tree(value, parent, key)
            return

        elif type(parent) == DictTreeItem:
            print("jpña")
            if type(value) == list:
                item2 = DictionaryEntry(parent, key, "[]")
                item = ListTreeItem(item2,["[]"])
                for i, value in enumerate(value):
                    self.populate_tree(value, item, i)

            elif type(value) == dict:
                item2 = DictionaryEntry(parent, key, "{}")
                item = DictTreeItem(item2, key)
                for key, value in value.items():
                    self.populate_tree(value, item, key)
                parent.addChild(item)
            else:
                item = DictionaryValueItem(parent, key, value)
                parent.addChild(item)
        elif type(parent) == ListTreeItem:
            if type(value) == list:
                item = ListTreeItem(parent, ["[]"])
                for i, value in enumerate(value):
                    self.populate_tree(value, item, i)
                parent.addChild(item)
            elif type(value) == dict:
                item = DictTreeItem(parent, ["{}"])
                for key, value in value.items():
                    self.populate_tree(value, item, key)
                parent.addChild(item)
            else:
                item = ValueItem(parent, value, key)
                parent.addChild(item)


    def traverse_tree(self, item, output=None):
        print("Traverse tree", item, type(item))
        pass

        '''
        elif type(item) == ListTreeItem:
            if output is None:
                output = []
            else:
        '''

        # Recursively traverse children
        # for i in range(item.childCount()):
        #    print("Child:", type(item.child(i)))
        #    self.traverse_tree(item.child(i))


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("QTreeWidget Example")
        self.setGeometry(100, 100, 600, 400)

        self.tree_widget = DictTreeWidget()
        self.tree_widget.populate_tree({1: 44, 2: [1, 2, 3, {1: 2} ,  [3,5,6]], 4:{1:4}}, None)
        self.out = {}
        self.tree_widget.traverse_tree(self.tree_widget.invisibleRootItem(), self.out)
        print("Output", self.out)
        self.tree_widget.setHeaderLabels(["Name", "Value"])
        self.setCentralWidget(self.tree_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
