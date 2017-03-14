import os
import re
import time
import BuildUiFiles
import subprocess
import zipfile

# Alias native new line character
nl = os.linesep


def find_release(File):
    """ Function to parse files and find the release

    A better way to do this would probably be to import the TestCommander module
    and pull the release that way, but importing TestCommander involves importing
    a large amount of other modules that aren't on the path when outside of trunk
    as we are here. This is the next best option that I saw.
    """
    with open(File, 'rb') as fid:
        for line in fid:
            c = re.search("__release__\s*=\s*'(.*)'", line)
            if c:
                return c.groups()[0]
    return ''


def main():
    """ Create meta data and build executable

    This function creates the build_info file that is wrapped into the
    executable. It also compiles the UI files and crates the init file in the
    UI_Files folder making it a package. It then compiles the executable by
    calling the main function of the build file in PyInstaller. The building of
    the executable is wrapped in a try statement and will message that the
    build failed upon any error.

    """
    print("Creating build_info file")
    # First make a build log with all the revisions and the date and time
    # this file gets wrapped into the executable
    build_time = time.strftime("%Y/%m/%d - %H:%M:%S")
    release = find_release('src/shared.py')
    with open("build_info", "wb") as log:
        # Write the build time
        log.write("Build Time: ")
        log.write(build_time + nl)
        # Write the Release
        log.write("Release: {}".format(release) + nl)

    # Build the UI_Files
    print("Building UI files")
    BuildUiFiles.main('', [r'src\UIFiles', r'src\genericdialogs\UIFiles'])

    print("PyInstaller Building executable")
    # Build the executable
    subprocess.call('pyinstaller PhotoOrganizer.spec')

    # Compress into Zip
    print("Compressing the Executable")
    zname = r'dist\PhotoOrganizer.zip'
    path = 'dist/PhotoOrganizer/'
    zipf = zipfile.ZipFile(zname, 'w')
    for root, _, files in os.walk(path):
        relative = root.replace('dist/', '')
        for f in files:
            zipf.write(os.path.join(root, f), os.path.join(relative, f))
    zipf.close()

    # Build the installer
    print("PyInstaller Building Setup Executable")
    subprocess.call('pyinstaller PhotoOrganizerSetp.spec')

    # Remove the zip file
    os.remove('dist/PhotoOrganizer.zip')

    raw_input("Done")

if __name__ == '__main__':
    main()
