""" 
:Author: Jonathan Karr <jonrkarr@gmail.com>
:Date: 2017-05-03
:Copyright: 2017, Karr Lab
:License: MIT
"""

from wc_utils import backup
import ftputil
import mock
import os
import shutil
import six
import tempfile
import unittest
import wc_utils.util.git

if six.PY3:
    from test.support import EnvironmentVarGuard
else:
    from test.test_support import EnvironmentVarGuard


class TestBackupManager(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

        env = EnvironmentVarGuard()

        if not os.getenv('CODE_SERVER_HOSTNAME'):
            with open('tests/fixtures/secret/CODE_SERVER_HOSTNAME', 'r') as file:
                env.set('CODE_SERVER_HOSTNAME', file.read().rstrip())

        if not os.getenv('CODE_SERVER_USERNAME'):
            with open('tests/fixtures/secret/CODE_SERVER_USERNAME', 'r') as file:
                env.set('CODE_SERVER_USERNAME', file.read().rstrip())

        if not os.getenv('CODE_SERVER_PASSWORD'):
            with open('tests/fixtures/secret/CODE_SERVER_PASSWORD', 'r') as file:
                env.set('CODE_SERVER_PASSWORD', file.read().rstrip())

        if not os.getenv('CODE_SERVER_REMOTE_DIRNAME'):
            with open('tests/fixtures/secret/CODE_SERVER_REMOTE_DIRNAME', 'r') as file:
                env.set('CODE_SERVER_REMOTE_DIRNAME', file.read().rstrip())

        self.manager = backup.BackupManager(archive_filename=os.path.join(self.tempdir, 'test.wc_utils.backup.txt.tar.gz'),
                                            archive_remote_filename='test.wc_utils.backup.txt.tar.gz')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

        manager = self.manager

        with ftputil.FTPHost(manager.hostname, manager.username, manager.password) as ftp:
            dirname = ftp.path.join(manager.remote_dirname, manager.archive_remote_filename)

            # remove directory for uploads
            if ftp.path.isdir(dirname):
                ftp.rmtree(dirname)

    def test(self):
        content = 'this is a test'
        filename = os.path.join(self.tempdir, 'test.wc_utils.backup.txt')
        with open(filename, 'w') as file:
            file.write(content)

        content2 = 'this is a test 2'
        filename2 = os.path.join(self.tempdir, 'test.wc_utils.backup.2.txt')
        with open(filename2, 'w') as file:
            file.write(content2)

        manager = self.manager
        self.assertEqual(manager.archive_filename, filename + '.tar.gz')

        # create
        files = [
            backup.BackupFile(filename, 'test.wc_utils.backup.txt'),
            backup.BackupFile(filename2, 'test.wc_utils.backup.2.txt'),
        ]
        for file in files:
            file.set_created_modified_time()
            file.set_username_ip()
            file.set_program_version_from_repo()
        manager.create(files)
        self.assertTrue(os.path.isfile(manager.archive_filename))

        # upload
        manager.upload()

        # download
        manager.archive_filename = filename + '.2.tar.gz'
        manager.download()

        self.assertTrue(os.path.isfile(manager.archive_filename))

        # extract
        os.remove(filename)
        files_down = [
            backup.BackupFile(filename, 'test.wc_utils.backup.txt'),
            backup.BackupFile(filename2, 'test.wc_utils.backup.2.txt'),
        ]
        manager.extract(files_down)

        with open(filename, 'r') as file:
            self.assertEqual(file.read(), content)

        with open(filename2, 'r') as file:
            self.assertEqual(file.read(), content2)

        for file, file_down in zip(files, files_down):
            self.assertEqual(file.program, file_down.program)
            self.assertEqual(file.version, file_down.version)
            self.assertEqual(file.username, file_down.username)
            self.assertEqual(file.ip, file_down.ip)
            self.assertEqual(file.created, file_down.created)
            self.assertEqual(file.modified, file_down.modified)

        manager.cleanup()
