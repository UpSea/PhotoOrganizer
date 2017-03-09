#!/usr/bin/python
# Orginal Author: Lucas McNinch
# Orignal Creation Date: 2014/10/29

import sys
import os
import re
import argparse
import shutil
import traceback


#Get the build info
def resource_path(relative):
    return os.path.join(getattr(sys, "_MEIPASS",
                                os.path.abspath(os.path.dirname(__file__))),
                        relative)

BUILD_INFO_FILE = resource_path('build_info')
if os.path.exists(BUILD_INFO_FILE):
    with open(BUILD_INFO_FILE, 'rb') as fid:
        BUILD_TIME = fid.readline()
        c = re.search('Release:\s*(.*)', fid.readline())
        RELEASE = c.groups()[0] if c else 'No Release Found'
else:
    BUILD_TIME = "No Build Info"
    RELEASE = 'No Release Found'


def main(path):
    """ Install Photo Organizer

    This function extracts PhotoOrganizer.zip to the user root and adds a
    shortcut to the desktop.

    Arguments:
    path        The location to which the application will be extracted
    """
    from zipfile import ZipFile
    import win32com.client

    #Remove the existing installation
    tcpath = os.path.join(path, 'PhotoOrganizer')
    if os.path.exists(tcpath):
        try:
            shutil.rmtree(tcpath)
        except:
            print('Failed to remove existing Photo Organizer installation.\n'
                  'An instance of Photo Organizer may be open.\n'
                  'Close all instances of Photo Organizer and try again.')
            raw_input('Press Enter to Exit')
            return

    #Get the full path to the zip file, whether this is run via python or as
    #an executable
    fname = resource_path('PhotoOrganizer.zip')

    #Open the zip file the zip file
    z = ZipFile(fname)
    #Extract each file in the zip file
    files = z.namelist()
    nfiles = len(files)
    msg = ''
    for k, f in enumerate(files):
        print(' '*len(msg) + '\r'),
        msg = 'Extracting {} of {}: {}\r'.format(k+1, nfiles, f)
        print(msg),
        z.extract(f, path)
    print

    #Add desktop shortcut
    #http://www.gossamer-threads.com/lists/python/python/117996
    shell = win32com.client.Dispatch('WScript.shell')
    desktop = shell.SpecialFolders('Desktop')

    shorty = shell.CreateShortcut(os.path.join(desktop, 'PhotoOrganizer - Shortcut.lnk'))
    shorty.TargetPath = os.path.join(path, r'PhotoOrganizer\PhotoOrganizer.exe')
    shorty.WindowStyle = 1
    # shorty.IconLocation = shorty.TargetPath
    shorty.Description = "Photo Organizer Shortcut"
    # shorty.WorkingDirectory = desktop
    shorty.Save()

    #Prompt to add shortcut for Configure Dewe Project
    msg = raw_input('Installation Complete'
                    '\nA shortcut has been added to your desktop'
                    '\nPress Enter or close this window')

if __name__ == "__main__":
    #Add arguments for install location, shortcut or not, etc.
    desc = """Photo Organizer Setup {}\n""".format(RELEASE)
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    #Add version argument
    version = 'Photo Organizer Release: {}'.format(RELEASE)
    version += '\n{}'.format(BUILD_TIME)
    parser.add_argument('-v', '--version', action='version', version=version)

    #Parse arguments
    args = parser.parse_args()

    #Create the installation path in the user directory
    from src import shared
    path = shared.installDir

    #Warn the user that you're going to install
    boundary = '-'*len(desc)
    warning = 'Previous Installations will be overwritten'
    wbound = '!'*len(warning)
    msg = '\n{1}{0}\n\n'.format(boundary, desc) +\
          'This application will extract Photo Organizer to\n{}'.format(path) +\
          '\nand create a shortcut to the application ' +\
          'on your Desktop.\n\n{0}\n{1}\n{0}\n\n'.format(wbound, warning) +\
          'Do you want to continue? y or (n)'
    inp = raw_input(msg)
    if inp.lower() == 'y':
        try:
            main(path)
        except:
            traceback.print_exc()
            raw_input('\nInstallation Aborted. Press Enter to Exit.')
    else:
        raw_input('\nInstallation Aborted. Press Enter to Exit.')
