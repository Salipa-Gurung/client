# -*- coding: utf-8 -*-
import os
from os.path import isfile, join, isdir
import re
import builtins
import shutil

from pageObjects.AccountSetting import AccountSetting

from helpers.SetupClientHelper import getUserSyncPath, getResourcePath
from helpers.FilesHelper import buildConflictedRegex, sanitizePath
from helpers.SyncHelper import waitForClientToBeReady


def folderExists(folderPath, timeout=1000):
    return waitFor(
        lambda: isdir(sanitizePath(folderPath)),
        timeout,
    )


def fileExists(filePath, timeout=1000):
    return waitFor(
        lambda: isfile(sanitizePath(filePath)),
        timeout,
    )


# To create folders in a temporary directory, we set isTempFolder True
# And if isTempFolder is True, the createFolder function create folders in tempFolderPath
def createFolder(context, foldername, username=None, isTempFolder=False):
    syncPath = None
    if username and not isTempFolder:
        syncPath = getUserSyncPath(context, username)
    elif isTempFolder:
        syncPath = context.userData['tempFolderPath']
    else:
        syncPath = context.userData['currentUserSyncPath']
    path = join(syncPath, foldername)
    os.makedirs(path)


def renameFileFolder(context, source, destination):
    source = join(context.userData['currentUserSyncPath'], source)
    destination = join(context.userData['currentUserSyncPath'], destination)
    os.rename(source, destination)


def createFileWithSize(context, filename, filesize, isTempFolder=False):
    if isTempFolder:
        path = context.userData['tempFolderPath']
    else:
        path = context.userData['currentUserSyncPath']
    file = join(path, filename)
    cmd = "truncate -s {filesize} {file}".format(filesize=filesize, file=file)
    os.system(cmd)


def writeFile(resource, content):
    f = open(resource, "w")
    f.write(content)
    f.close()


def waitAndWriteFile(context, path, content):
    waitForClientToBeReady(context)
    writeFile(path, content)


def waitAndTryToWriteFile(context, resource, content):
    waitForClientToBeReady(context)
    try:
        writeFile(resource, content)
    except:
        pass


@When(
    'user "|any|" creates a file "|any|" with the following content inside the sync folder'
)
def step(context, username, filename):
    fileContent = "\n".join(context.multiLineText)
    syncPath = getUserSyncPath(context, username)
    waitAndWriteFile(context, join(syncPath, filename), fileContent)


@When('user "|any|" creates a folder "|any|" inside the sync folder')
def step(context, username, foldername):
    createFolder(context, foldername, username)


@Given('user "|any|" has created a folder "|any|" inside the sync folder')
def step(context, username, foldername):
    createFolder(context, foldername, username)


@When('user "|any|" creates a file "|any|" with size "|any|" inside the sync folder')
def step(context, username, filename, filesize):
    createFileWithSize(context, filename, filesize)


@When('the user copies the folder "|any|" to "|any|"')
def step(context, sourceFolder, destinationFolder):
    source_dir = join(context.userData['currentUserSyncPath'], sourceFolder)
    destination_dir = join(context.userData['currentUserSyncPath'], destinationFolder)
    shutil.copytree(source_dir, destination_dir)


@When(r'the user renames a (file|folder) "([^"]*)" to "([^"]*)"', regexp=True)
def step(context, type, source, destination):
    renameFileFolder(context, source, destination)


@Then('the file "|any|" should exist on the file system with the following content')
def step(context, filePath):
    expected = "\n".join(context.multiLineText)
    filePath = context.userData['currentUserSyncPath'] + filePath
    f = open(filePath, 'r')
    contents = f.read()
    test.compare(
        expected,
        contents,
        "file expected to exist with content "
        + expected
        + " but does not have the expected content",
    )


@Then(r'^the (file|folder) "([^"]*)" should exist on the file system$', regexp=True)
def step(context, resourceType, resource):
    resourcePath = join(context.userData['currentUserSyncPath'], resource)
    resourceExists = False
    if resourceType == 'file':
        resourceExists = fileExists(
            resourcePath, context.userData['maxSyncTimeout'] * 1000
        )
    elif resourceType == 'folder':
        resourceExists = folderExists(
            resourcePath, context.userData['maxSyncTimeout'] * 1000
        )
    else:
        raise Exception("Unsupported resource type '" + resourceType + "'")

    test.compare(
        True,
        resourceExists,
        "Assert " + resourceType + " '" + resource + "' exists on the system",
    )


@Then(r'^the (file|folder) "([^"]*)" should not exist on the file system$', regexp=True)
def step(context, resourceType, resource):
    resourcePath = join(context.userData['currentUserSyncPath'], resource)
    resourceExists = False
    if resourceType == 'file':
        resourceExists = fileExists(resourcePath, 1000)
    elif resourceType == 'folder':
        resourceExists = folderExists(resourcePath, 1000)
    else:
        raise Exception("Unsupported resource type '" + resourceType + "'")

    test.compare(
        False,
        resourceExists,
        "Assert " + resourceType + " '" + resource + "' doesn't exist on the system",
    )


@Given('the user has changed the content of local file "|any|" to:')
def step(context, filename):
    fileContent = "\n".join(context.multiLineText)
    waitAndWriteFile(
        context, join(context.userData['currentUserSyncPath'], filename), fileContent
    )


@Then(
    'a conflict file for "|any|" should exist on the file system with the following content'
)
def step(context, filename):
    expected = "\n".join(context.multiLineText)

    onlyfiles = [
        f
        for f in os.listdir(context.userData['currentUserSyncPath'])
        if isfile(join(context.userData['currentUserSyncPath'], f))
    ]
    found = False
    pattern = re.compile(buildConflictedRegex(filename))
    for file in onlyfiles:
        if pattern.match(file):
            f = open(context.userData['currentUserSyncPath'] + file, 'r')
            contents = f.read()
            if contents == expected:
                found = True
                break

    if not found:
        raise Exception("Conflict file not found with given name")


@When('the user overwrites the file "|any|" with content "|any|"')
def step(context, resource, content):
    print("starting file overwrite")
    resource = join(context.userData['currentUserSyncPath'], resource)
    waitAndWriteFile(context, resource, content)
    print("file has been overwritten")


@When('the user tries to overwrite the file "|any|" with content "|any|"')
def step(context, resource, content):
    resource = context.userData['currentUserSyncPath'] + resource
    waitAndTryToWriteFile(context, resource, content)


@When('user "|any|" tries to overwrite the file "|any|" with content "|any|"')
def step(context, user, resource, content):
    resource = getResourcePath(context, resource, user)
    waitAndTryToWriteFile(context, resource, content)


@When(r'the user deletes the (file|folder) "([^"]*)"', regexp=True)
def step(context, itemType, resource):
    waitForClientToBeReady(context)

    resourcePath = sanitizePath(context.userData['currentUserSyncPath'] + resource)
    if itemType == 'file':
        os.remove(resourcePath)
    elif itemType == 'folder':
        shutil.rmtree(resourcePath)
    else:
        raise Exception("No such item type for resource")

    isSyncFolderEmpty = True
    for item in os.listdir(context.userData['currentUserSyncPath']):
        # do not count the hidden files as they are ignored by the client
        if not item.startswith("."):
            isSyncFolderEmpty = False
            break

    # if the sync folder is empty after deleting file,
    # a dialog will popup asking to confirm "Remove all files"
    if isSyncFolderEmpty:
        try:
            AccountSetting.confirmRemoveAllFiles()
        except:
            pass


@When('user "|any|" creates the following files inside the sync folder:')
def step(context, username):
    syncPath = getUserSyncPath(context, username)

    waitForClientToBeReady(context)

    for row in context.table[1:]:
        filename = syncPath + row[0]
        writeFile(join(syncPath, filename), '')


@Given(
    'the user has created a folder "|any|" with "|any|" files each of size "|any|" bytes in temp folder'
)
def step(context, foldername, filenumber, filesize):
    createFolder(context, foldername, isTempFolder=True)
    filesize = builtins.int(filesize)
    for i in range(0, builtins.int(filenumber)):
        filename = f"file{i}.txt"
        createFileWithSize(context, join(foldername, filename), filesize, True)


@When('user "|any|" moves folder "|any|" from the temp folder into the sync folder')
def step(context, username, foldername):
    source_dir = join(context.userData['tempFolderPath'], foldername)
    destination_dir = getUserSyncPath(context, username)
    shutil.move(source_dir, destination_dir)
