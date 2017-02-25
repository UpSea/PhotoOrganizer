""" Undo commands for Photo Organizer """
from PyQt4 import QtGui


class newFieldCmd(QtGui.QUndoCommand):
    """ Undo command for inserting a new field into the album

    Arguments:
        main (PhotoOrganizer): The instance of the main app
        name (str, QString): The name of the new field
    """
    def __init__(self, main, name, parent=None):
        super(newFieldCmd, self).__init__(parent)
        self.main = main
        self.name = str(name)

    def redo(self):
        name = self.name
        self.main.model.insertColumns(name=name)
        newfield = self.main.fields[-1]
        newfield.filter = True
        newfield.tags = True
        self.main.db.insertField(newfield)

    def undo(self):
        col = self.main.fields.index(self.name)
        self.main.db.dropField(self.name)
        self.main.model.removeColumns(col)
