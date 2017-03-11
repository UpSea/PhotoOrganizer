""" Undo commands for Photo Organizer """
from PyQt4 import QtGui
from shared import trashDir
import shutil
from datetime import datetime
import os


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


class removeRowCmd(QtGui.QUndoCommand):
    """ Undo command for removing a photo

    Arguments:
        main (PhotoOrganizer): The main application instance
        photo (Photo): The photo object to be deleted
    """

    description = "Delete Photo"

    def __init__(self, main, photo, parent=None):
        self.main = main
        self.photo = photo
        self.row = main.album.index(photo)
        description = self.description.replace('Photo', photo.fileName)
        super(removeRowCmd, self).__init__(description, parent)

    def redo(self):
        # Remove the photo
        self.main.model.removeRows(self.row)
        self.main.db.deleteFile(self.photo.fileId)

        # Select the next row
        newRow = self.row
        if len(self.main.album) <= self.row:
            newRow = len(self.main.album)
        self.main.view.setCurrentPhoto(newRow)

        # Move the file to the trash
        trashTime = datetime.now().strftime('.%Y%m%d%H%M%S')
        self.trashFile = os.path.join(trashDir, self.photo.fileName + trashTime)
        shutil.move(self.photo.filePath, self.trashFile)

    def undo(self):
        # Re-insert the photo
        self.main.model.insertRows(self.row, entry=self.photo)
        self.main.db.insertFile(self.photo)

        # Select our row
        self.main.view.setCurrentPhoto(self.row)

        # Restore the file from the trash
        shutil.move(self.trashFile, self.photo.filePath)
