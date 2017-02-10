from PyQt4 import QtGui


class PhotoTable(QtGui.QTableView):

    def rehideColumns(self):
        fields = self.model().sourceModel().dataset.fields
        hide = [k.hidden for k in fields]
        [self.setColumnHidden(k, v) for k, v in enumerate(hide)]
