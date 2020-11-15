from configparser import ConfigParser
import subprocess
import threading
from queue import Queue, Empty

import PySimpleGUI as sg


# TODO: Allow configuring a task with environment variables and CWD
# TODO: Show output of long running process in a follow-mode
# TODO: Show the status of a currently running process
# TODO: Allow switching between scripts to see current or last output
# TODO: Pull script list from a folder
# TODO: Keep logs on disk
# TODO: Add parameters configured by encoded script comments
# TODO: Watch directory or files to trigger tasks


class AsynchronousFileReader(threading.Thread):
    '''
    Helper class to implement asynchronous reading of a file
    in a separate thread. Pushes read lines on a queue to
    be consumed in another thread.
    '''

    def __init__(self, fd, queue):
        assert isinstance(queue, Queue)
        assert callable(fd.readline)
        threading.Thread.__init__(self)
        self._fd = fd
        self._queue = queue
        self.daemon = True

    def run(self):
        '''The body of the tread: read lines and put them on the queue.'''
        for line in iter(self._fd.readline, ''):
            self._queue.put(line)

    def eof(self):
        '''Check whether there is no more content to expect.'''
        return not self.is_alive() and self._queue.empty()


def run_process(command):
    # Launch the command as subprocess.
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Launch the asynchronous readers of the process' stdout and stderr.
    stdout_queue = Queue()
    stdout_reader = AsynchronousFileReader(process.stdout, stdout_queue)
    stdout_reader.start()
    stderr_queue = Queue()
    stderr_reader = AsynchronousFileReader(process.stderr, stderr_queue)
    stderr_reader.start()

    return stdout_queue, stderr_queue


cfg = ConfigParser()
cfg.read(".charlie.yaml")


sg.theme('DarkAmber')   # Add a touch of color

cmd_output = sg.Multiline(size=(120, 50), key='$OUTPUT', font="Consolas")
cmd_input = sg.InputText(key='$INPUT')

scripts = []
for section in cfg.sections():
    if section.startswith('job.'):
        if 'command' in cfg[section]:
            scripts.append(cfg[section]['command'])

# All the stuff inside your window.
layout = [
    [sg.Text('Some text on Row 1')],
    [sg.Listbox(scripts, size=(60, 10), key='$SCRIPTS', enable_events=True)],
    [sg.Text('Run ad-hoc command:'), cmd_input],
    [sg.Button('Ok'), sg.Button('Cancel')],
    [cmd_output],
]

# Create the Window
window = sg.Window('Charlie', layout)

# Event Loop to process "events" and get the "values" of the inputs
q_out: Queue = None
q_err: Queue = None
while True:
    event, values = window.read(5)
    if event == '__TIMEOUT__':
        for queue in (q_out, q_err):
            if queue:
                more = []
                for _ in range(100):
                    try:
                        more.append(queue.get_nowait().decode('utf8').replace('\r\n', '\n'))
                    except Empty:
                        break
                more = ''.join(more)
                if more:
                    current = cmd_output.get()[:-1] # trim extra \n
                    cmd_output.update(current + more)
                    cmd_output.set_vscroll_position(1.0)
            continue
    elif event == sg.WIN_CLOSED or event == 'Cancel': # if user closes window or clicks cancel
        break
    elif event == '$SCRIPTS':
        cmd_input.update(values['$SCRIPTS'][0])
        continue
    elif event == 'Ok':
        cmd = values['$INPUT']
        if cmd:
            cmd_output.update("")
            q_out, q_err = run_process(cmd)
    else:
        print((event, values))

window.close()