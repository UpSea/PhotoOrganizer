import shutil
from threading import Event as thread_Event


class Mover(object):
    """File Move class

    This class is meant for moving and copying files.The class can
    be initialized empty and the methods called directly, or, for threaded
    operation, arguments given upon instantiation will be given to
    upload_files by the work method, which is intended to be called in a
    thread. This class is intented to be used inconjuncion with ProgressDialog

    Arguments:
        files ([(str,str)]): A list of tuples. The tuples are passed as
            arguments to shutil.move or shutil.copy depending on moveFun
        moveFun (MOVE,COPY): (COPY) The function to apply to the files.
            Mover.MOVE and Mover.COPY are references to shutil.move and
            shutil.copy for convenience.
    """

    MOVE = staticmethod(shutil.move)
    COPY = staticmethod(shutil.copy2)

    def __init__(self, files=None, moveFun=shutil.copy):
        self.files = files
        self.moveFun = moveFun

        # Initialize Status
        self.active = thread_Event()
        self.cancelEvent = thread_Event()
        self.status = ''
        self.progress = 0
        self.typeStr = "Copying" if moveFun == self.COPY else "Moving"

    def work(self):
        """ Does the work of copying or moving the files

        Intended to be run in a thread by a progress dialog. Sets status and
        progress properties
        """
        # Copy the files
        self.active.set()
        numFiles = float(len(self.files))
        curfile = 0
        for f in self.files:
            if self.cancelEvent.isSet():
                break
            self.progress = curfile/numFiles*100
            curfile += 1
            addStr = ': %d of %d (%s)' % (curfile, numFiles, f[0])
            self.status = self.typeStr + addStr
            self.moveFun(*f)

        self.status = 'Finished %s %d file(s)' % (self.typeStr.lower(), numFiles)
        self.active.clear()

    def cancel(self):
        """ Cancel the process """
        self.cancelEvent.set()
