import sublime
import sublime_plugin

from . import cfparser
import os
import subprocess
from urllib.request import urlopen
from urllib.parse import urlparse
# from urllib.error import URLError
import itertools
import threading
# import sys

url = ''


class Environment(sublime_plugin.TextCommand):

    def __init__(self, view):
        super().__init__(view)
        self.num_tests = 0

    def get_variables(self):

        try:
            self.window = self.view.window()
            self.vars = self.window.extract_variables()
            self.file_extension = self.vars['file_extension']
            self.file_name = self.vars['file_base_name']
            self.file = self.vars['file']
            self.working_dir = self.vars['file_path']
            self.classpath = self.working_dir
        except KeyError:
            sublime.error_message('Please save your file before continuing ')
            raise

        return self.file_extension, self.file_name, self.file, self.working_dir, self.classpath


class RunCommand(Environment):

    panel = None
    panel_lock = threading.Lock()

    def run(self, edit):

        settings = sublime.load_settings("easycp.sublime-settings")
        file_extension, file_name, file, working_dir, classpath = self.get_variables()

        if file_extension not in ('java', 'py', 'py3', 'cpp'):
            sublime.error_message('.' + file_extension + ' extension is not supported')
            return

        def get_num_tests():

            self.input_dir = os.path.join(working_dir, file_name, 'input')
            self.output_dir = os.path.join(working_dir, file_name, 'output')
            self.myout_dir = os.path.join(working_dir, file_name, 'myoutput')
            try:
                self.num_tests = len(os.listdir(self.input_dir))
            except FileNotFoundError:
                sublime.error_message('You must parse the test-cases first')
                raise
            return self.num_tests

        def get_output():

            if file_extension == 'java':
                cmd = settings.get("java_run", "java")
                if type(cmd) is not list:
                    cmd = [cmd]
                cmd += ['java', '-cp', classpath, file_name]

            elif file_extension in ("py", "py3"):
                cmd = settings.get("python_run", ["py", "-3"])
                if type(cmd) is not list:
                    cmd = [cmd]
                cmd += [file]

            elif file_extension == "cpp":
                cmd = settings.get("cpp_run", "")
                if type(cmd) is not list:
                    cmd = [cmd]
                cmd += [os.path.join(working_dir, file_name + ".exe")]

            while '' in cmd:
                cmd.remove('')

            for i in range(1, self.num_tests + 1):

                with open(os.path.join(self.input_dir, 'in' + str(i))) as in_file, \
                        open(os.path.join(self.myout_dir, 'out' + str(i)), "w") as out_file:

                    subprocess.call(cmd, stdin=in_file, stdout=out_file)

        def display_output():

            msg = ''
            for i in range(1, self.num_tests + 1):
                msg += "************Executing Test-Case {}************\n".format(i)
                in_file = os.path.join(self.input_dir, 'in' + str(i))
                out_file = os.path.join(self.output_dir, 'out' + str(i))
                myout_file = os.path.join(self.myout_dir, 'out' + str(i))

                with open(in_file, "r") as f1, open(out_file, "r") as f2, open(myout_file, "r") as f3:
                    msg += "Input:\n{}Expected Output:\n{}Your Output:\n{}Status: {}\n\n".format(
                        f1.read(), f2.read(), f3.read(), compare_output(out_file, myout_file)
                    )

            with self.panel_lock:
                self.panel = self.window.create_output_panel('panel')
                self.panel.set_read_only(False)
                self.panel.run_command("append", {"characters": msg})
                self.panel.set_read_only(True)
                self.window.run_command('show_panel', {"panel": "output.panel"})

        def compare_output(out_file, myout_file):

            with open(myout_file, "r") as f1, open(out_file, "r") as f2:

                for line1, line2 in itertools.zip_longest(f1, f2):
                    if line1 is not None and line2 is not None:
                        if line1.strip() and line2.strip() and line1 != line2:
                            return "FAILED"

                    elif line1 is not None or line2 is not None:
                        return "FAILED"

            return "Passed Successfuly"

        self.num_tests = get_num_tests()
        get_output()
        display_output()


class CompileCommand(Environment):

    proc = None
    panel = None
    encoding = 'utf-8'
    panel_lock = threading.Lock()
    killed = False

    def run(self, edit):

        settings = sublime.load_settings("easycp.sublime-settings")
        file_extension, file_name, file, working_dir, classpath = self.get_variables()

        commands = {}
        for lang, default in [('java', 'javac'), ('cpp', "g++")]:
            cmd = settings.get(lang + "_compile", default)
            if type(cmd) is not list:
                cmd = [cmd]
            while '' in cmd:
                cmd.remove('')
            commands[lang] = cmd

        if file_extension == 'java':
            cmd = commands['java'] + [file]
        elif file_extension == "cpp":
            cmd = commands['java'] + [file, "-o", os.path.join(working_dir, file_name + ".exe")]
        elif file_extension in ('py', 'py3'):
            sublime.message_dialog("Python does not need compilation")
            return
        else:
            sublime.error_message('.' + file_extension + ' extension is not supported')
            return

        with self.panel_lock:
            self.panel = self.window.create_output_panel('exec')
            settings = self.panel.settings()
            settings.set(
                'result_file_regex',
                r'^File "([^"]+)" line (\d+) col (\d+)'
            )
            settings.set(
                'result_line_regex',
                r'^\s+line (\d+) col (\d+)'
            )
            settings.set('result_base_dir', working_dir)

            self.window.run_command('show_panel', {'panel': 'output.exec'})

        if self.proc is not None:
            self.proc.terminate()
            self.proc = None

        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
        self.proc.wait()

        threading.Thread(
            target=self.read_handle,
            args=(self.proc.stderr,)
        ).start()

    def read_handle(self, handle):

        chunk_size = 2 ** 13
        out = b''
        while True:
            try:
                data = os.read(handle.fileno(), chunk_size)
                out += data
                if len(data) == chunk_size:
                    continue
                if data == b'' and out == b'':
                    raise IOError('EOF')
                self.queue_write(out.decode(self.encoding))
                if data == b'':
                    raise IOError('EOF')
                out = b''
            except UnicodeDecodeError as e:
                msg = 'Error decoding output using %s - %s'
                self.queue_write(msg % (self.encoding, str(e)))
                break
            except IOError:
                if self.killed:
                    msg = 'Cancelled'
                else:
                    msg = 'Finished'
                self.queue_write('\n[%s]' % msg)
                break

    def queue_write(self, text):
        sublime.set_timeout(lambda: self.do_write(text), 1)

    def do_write(self, text):
        with self.panel_lock:
            self.panel.run_command('append', {'characters': text})


class ParseUrlCommand(Environment):

    def run(self, edit):

        file_extension, file_name, file, working_dir, classpath = self.get_variables()

        def on_done(url):
            # Check url
            if "codeforces" not in urlparse(url, allow_fragments=False).netloc:
                sublime.error_message('EasyCP supports only codefores.com')
                raise

            # Create new directory structure to store sample input,
            # sample output and output generated my user's code

            input_fp = os.path.join(working_dir, file_name, 'input')
            if not os.path.exists(input_fp):
                os.makedirs(input_fp)
            output_fp = os.path.join(working_dir, file_name, 'output')
            if not os.path.exists(output_fp):
                os.makedirs(output_fp)
            myoutput_fp = os.path.join(working_dir, file_name, 'myoutput')
            if not os.path.exists(myoutput_fp):
                os.makedirs(myoutput_fp)

            parse_url(url, input_fp, output_fp)

        def parse_url(url, input_fp, output_fp):
            # Parses test cases
            try:
                html = urlopen(url).read()
            except Exception:
                sublime.error_message('URL Error')
                raise

            parser = cfparser.CFParser(input_fp, output_fp)
            parser.feed(html.decode('utf-8'))

        sublime.active_window().show_input_panel("Insert URL", url, on_done, None, None)
