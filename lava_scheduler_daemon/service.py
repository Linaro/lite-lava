import json
import logging
import os
import tempfile

from twisted.application.service import Service
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ProcessProtocol
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.threads import deferToThread
from twisted.python.filepath import FilePath


def defer_to_thread(func):
    def wrapper(*args, **kw):
        return deferToThread(func, *args, **kw)
    return wrapper


class DirectoryJobSource(Service):
    """
    A job source that looks in a directory.

    It looks for jobs (json files) in a subdirectory 'incoming' of the
    directory it is configured with.  Running jobs are moved to 'running' and
    completed jobs to 'completed'.
    """

    logger = logging.getLogger('DirectoryJobSource')

    def __init__(self, directory, polling_interval, scheduler_service):
        self.directory = directory
        self.polling_interval = polling_interval
        self.scheduler_service = scheduler_service
        self._call = LoopingCall(self.lookForJob)

    def startService(self):
        if not self.directory.isdir():
            self.logger.critical("%s is not a directory", self.directory)
            raise RuntimeError("%s must be a directory" % self.directory)
        for subdir in 'incoming', 'running', 'completed', 'broken':
            subdir = self.directory.child(subdir)
            if not subdir.isdir():
                subdir.createDirectory()
        self.logger.info("starting to look for jobs in %s", self.directory)
        self._call.start(self.polling_interval)

    def stopService(self):
        self._call.stop()

    def lookForJob(self):
        self.logger.info("Looking for a job in %s", self.directory)
        json_files = self.directory.child('incoming').globChildren("*.json")
        json_files.sort(key=lambda fp:fp.getModificationTime())
        busyBoards = self.busyBoards()
        for json_file in json_files:
            json_data = json.load(json_files[0].open())
            target = json_data['target']
            if target not in busyBoards:
                self.logger.info(
                    "Starting %s on %s", json_file, target)
                self.scheduler_service.jobSubmitted(
                    json_data, json_file.basename())
                break
            else:
                self.logger.info(
                    "Not executing %s because %s is busy", json_file, target)

    def markJobStarted(self, token):
        self.directory.child('incoming').child(token).moveTo(
            self.directory.child('running').child(token))

    def markJobCompleted(self, token, logpath):
        completed = self.directory.child('completed')
        counter = 0
        while True:
            fname = '%03d%s' % (counter, token)
            if not completed.child(fname).exists():
                break
            counter += 1
        self.directory.child('running').child(token).moveTo(
            completed.child(fname))
        FilePath(logpath).moveTo(
            completed.child(fname + '.output'))

    def _running_jsons(self):
        running_files = self.directory.child('running').globChildren("*.json")
        for json_file in running_files:
            yield (json.load(json_file.open()), json_file.basename())

    def busyBoards(self):
        return [json_data['target']
                for (json_data, token) in self._running_jsons()]

    def jobRunningOnBoard(self, hostname):
        for json_data, token in self._running_jsons():
            if json_data['target'] == hostname:
                return json_data, token
        else:
            return None


class DispatcherProcessProtocol(ProcessProtocol):

    def __init__(self, deferred):
        self.deferred = deferred
        fd, self._logpath = tempfile.mkstemp()
        self._output = os.fdopen(fd, 'wb')

    def outReceived(self, text):
        print 'received', repr(text)
        self._output.write(text)

    errReceived = outReceived

    def processEnded(self, reason):
        self._output.close()
        self.deferred.callback(self._logpath)


class LavaSchedulerService(Service):

    logger = logging.getLogger('LavaSchedulerService')

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def jobSubmitted(self, json_data, token):
        if json_data['target'] not in self.job_source.busyBoards():
            self.job_source.markJobStarted(token)
            self._dispatchJob(json_data).addCallback(self.jobCompleted)

    def jobCompleted(self, (hostname, logpath)):
        json_data, token = self.job_source.jobRunningOnBoard(hostname)
        self.job_source.markJobCompleted(token, logpath)

    def _dispatchJob(self, json_data):
        d = Deferred()
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, 'wb') as f:
            json.dump(json_data, f)
        def clean_up_file(result):
            self.logger.info("job finished on %s", json_data['target'])
            os.unlink(path)
            return (json_data['target'], result)
        d.addBoth(clean_up_file)
        reactor.spawnProcess(
            DispatcherProcessProtocol(d), self.dispatcher,
            args=[self.dispatcher, path], childFDs={0:0, 1:'r', 2:'r'})
        return d
