import sublime
import sublime_plugin

import os
from . import easycp_parser as Parser
from re import match as re_match, compile as re_compile
import subprocess
from urllib.parse import urlparse
from itertools import zip_longest
from threading import Thread, Lock


REGEX = {
    "cf_problem": re_compile(
        r"^.*[\/\\]*(?:contest[\/\\]+\d+[\/\\]+problem|problemsets?[\/\\]+(?:.+[\/\\]+)?problem[\/\\]+\d+)[\/\\]+(?:[A-Z]|\d)+$"
    ),
    "cf_problemset": re_compile(
        r"^.*[/\\]*contest[/\\]+\d+[/\\]*$"
    )
}
TEST_FILENAME = "test"


def mkpath(*paths) -> str:
    '''Combines paths and normalizes the result'''
    return os.path.normpath(os.path.join(*paths))


class Environment(sublime_plugin.TextCommand):
    '''File path data'''

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
        except KeyError:
            sublime.error_message("EasyCP: Please save your file before continuing")
            raise

        return self.file_extension, self.file_name, self.file, self.working_dir


class EasycpRunCommand(Environment):
    '''Handles "easycp_run" command'''

    panel = None
    panel_lock = Lock()

    def run(self, edit):

        settings = sublime.load_settings("easycp.sublime-settings")
        file_extension, file_name, file, working_dir = self.get_variables()

        if file_extension not in ('java', 'py', 'py3', 'cpp'):
            sublime.error_message("EasyCP: .{} extension is not supported".format(file_extension))
            raise

        def panel_print(message):
            # Prints message to self.panel
            with self.panel_lock:
                self.panel.set_read_only(False)
                self.panel.run_command("append", {"characters": message})
                self.panel.set_read_only(True)

        def run_tests():

            # Making paths
            self.input_dir = mkpath(working_dir, "EasyCP_" + file_name, 'input')
            self.output_dir = mkpath(working_dir, "EasyCP_" + file_name, 'output')
            self.myout_dir = mkpath(working_dir, "EasyCP_" + file_name, 'myoutput')

            # Creating folders if they don't exist
            if not os.path.exists(self.input_dir):
                os.makedirs(self.input_dir)
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
            if not os.path.exists(self.myout_dir):
                os.makedirs(self.myout_dir)

            # Getting names of test files
            self.test_files = os.listdir(self.input_dir)

            # If there are no test files
            if not self.test_files:
                sublime.error_message("EasyCP: You must parse or add the test-cases first")
                raise

            # Check if there is an output file for each input file
            for filename in self.test_files:
                if not os.path.exists(mkpath(self.output_dir, filename)):
                    sublime.error_message("Output file for \"{}\" not found".format(filename))
                    raise

            # Constructing command
            if file_extension == 'java':
                cmd = settings.get("java_run", "java")
                if type(cmd) is str:
                    cmd = list(cmd.split())
                cmd += ['-cp', mkpath(self.working_dir, "EasyCP_" + file_name), file_name]
                if not os.path.exists(mkpath(self.working_dir, "EasyCP_" + file_name, file_name + ".class")):
                    sublime.error_message("EasyCP: You must compile program first")
                    raise

            elif file_extension in ('py', 'py3'):
                cmd = settings.get("python_run", ['py', '-3'])
                if type(cmd) is str:
                    cmd = list(cmd.split())
                cmd += [file]

            elif file_extension == 'cpp':
                cmd = settings.get("cpp_run", "")
                if type(cmd) is str:
                    cmd = list(cmd.split())
                if not os.path.exists(mkpath(self.working_dir, "EasyCP_" + file_name, file_name + ".exe")):
                    sublime.error_message("EasyCP: You must compile program first")
                    raise

                cmd += [mkpath(working_dir, "EasyCP_" + file_name, file_name + ".exe")]

            # Removing empty strings
            while '' in cmd:
                cmd.remove('')

            # Creating output panel
            with self.panel_lock:
                self.panel = self.window.create_output_panel('EasyCP')
                self.panel.set_syntax_file("Packages/EasyCP/EasyCP.sublime-syntax")
                self.window.run_command('show_panel', {"panel": "output.EasyCP"})

            # Running a command for each test file
            for test_file in self.test_files:
                panel_print("************ Executing Test-Case \"{}\" ************\n".format(test_file))

                try:
                    # Excecuting
                    with open(mkpath(self.input_dir, test_file), 'r') as in_file, \
                            open(mkpath(self.myout_dir, test_file), 'w') as myout_file:
                        subprocess.call(cmd, shell=True, stdin=in_file, stdout=myout_file)

                    # Comparing and printing result
                    with open(mkpath(self.input_dir, test_file), 'r') as in_file, \
                            open(mkpath(self.output_dir, test_file), 'r') as out_file, \
                            open(mkpath(self.myout_dir, test_file), 'r') as myout_file:
                        out_data = out_file.read().strip()
                        myout_data = myout_file.read().strip()
                        panel_print("Input:\n{}\nExpected Output:\n{}\nYour Output:\n{}\nStatus: {}\n\n".format(
                            in_file.read(), out_data, myout_data,
                            "Passed Successfuly" if compare_output(out_data, myout_data) else "FAILED"
                        ))

                except Exception:
                    panel_print("Exception occurred while running \"{}\"\n\n".format(test_file))

        def compare_output(first_data, second_data):
            '''Compares data of two files'''

            for line1, line2 in zip_longest(first_data, second_data):
                if str(line1).rstrip() != str(line2).rstrip():
                    return False
            return True

        sublime.set_timeout_async(run_tests, 0)


class EasycpCompileCommand(Environment):
    '''Handles "easycp_compile" command'''

    proc = None
    panel = None
    encoding = 'utf-8'
    panel_lock = Lock()
    killed = False

    def run(self, edit):

        def comp():

            settings = sublime.load_settings("easycp.sublime-settings")
            file_extension, file_name, file, working_dir = self.get_variables()

            # Getting main commands from settings
            commands = {}
            for lang, default in [('java', 'javac'), ('cpp', "g++")]:
                cmd = settings.get(lang + "_compile", default)
                if type(cmd) is str:
                    cmd = list(cmd.split())
                commands[lang] = cmd

            # Contructing command
            if file_extension == 'java':
                cmd = commands['java'] + ["-d", mkpath(working_dir, "EasyCP_" + file_name), file]
            elif file_extension == "cpp":
                cmd = commands['cpp'] + [file, "-o", mkpath(working_dir, "EasyCP_" + file_name, file_name + ".exe")]
            elif file_extension in ('py', 'py3'):
                sublime.message_dialog("EasyCP: Python does not need compilation")
                return
            else:
                sublime.error_message("EasyCP: .{} extension is not supported".format(file_extension))
                raise

            # Removing empty strings
            while '' in cmd:
                cmd.remove('')

            # Creating folder
            if not os.path.exists(mkpath(working_dir, "EasyCP_" + file_name)):
                os.makedirs(mkpath(working_dir, "EasyCP_" + file_name))

            # Creating output panel
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

            # Killing last process if exists
            if self.proc is not None:
                self.proc.terminate()
                self.proc = None

            # Executing
            self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
            self.proc.wait()

            # Reading and printing answer
            Thread(
                target=self.read_handle,
                args=(self.proc.stderr,)
            ).start()

        sublime.set_timeout_async(comp, 0)

    def read_handle(self, handle):
        '''Reads output of a subprocess tread'''

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
                msg = "Error decoding output using %s - %s"
                self.queue_write(msg % (self.encoding, str(e)))
                break
            except IOError:
                if self.killed:
                    msg = "Cancelled"
                else:
                    msg = "Finished"
                self.queue_write('\n[%s]' % msg)
                break

    def queue_write(self, text):
        sublime.set_timeout(lambda: self.do_write(text), 1)

    def do_write(self, text):
        with self.panel_lock:
            self.panel.run_command('append', {'characters': text})


class EasycpParseUrlCommand(Environment):
    '''Handles "easycp_parse_url" command'''

    def run(self, edit):

        file_extension, file_name, file, working_dir = self.get_variables()

        def on_done(url):

            url_parts = urlparse(url, allow_fragments=True)

            # Checking URL
            if "codeforces" not in urlparse(url, allow_fragments=False).netloc:
                sublime.error_message("EasyCP supports only codefores.com")
                raise

            if re_match(REGEX["cf_problem"], url_parts.path):
                test_cases = Parser.CFProblem(url)

                store_problem(test_cases)

            elif re_match(REGEX["cf_problemset"], url_parts.path):
                problems = Parser.CFProblemset(url)

                for task_name in problems:
                    store_problem(problems[task_name], task_name)

            else:
                sublime.error_message("EasyCP can not recognize Codeforces URL")
                raise

        def store_problem(test_cases, name=file_name):

            # Creating input and output directories
            input_dir = mkpath(working_dir, "EasyCP_" + name, "input")
            if not os.path.exists(input_dir):
                os.makedirs(input_dir)
            output_dir = mkpath(working_dir, "EasyCP_" + name, "output")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Finding the largest number already used
            num_tests = 1
            while os.path.exists(mkpath(input_dir, TEST_FILENAME + str(num_tests))):
                num_tests += 1

            for test_case in test_cases:
                with open(mkpath(input_dir, TEST_FILENAME + str(num_tests)), 'w', encoding="utf-8") as input_file:
                    input_file.write(test_case[0])
                with open(mkpath(output_dir, TEST_FILENAME + str(num_tests)), 'w', encoding="utf-8") as input_file:
                    input_file.write(test_case[1])
                num_tests += 1

        sublime.active_window().show_input_panel("Insert URL", "",
                                                 lambda url: sublime.set_timeout_async(lambda: on_done(url), 0),
                                                 None, None)


class EasycpAddTestCommand(Environment):
    '''Handles "easycp_add_test" command'''

    def run(self, edit):

        file_extension, file_name, file, working_dir = self.get_variables()

        def on_done_input(input_data):

            # Creating input directory
            input_dir = mkpath(working_dir, "EasyCP_" + file_name, "input")
            if not os.path.exists(input_dir):
                os.makedirs(input_dir)

            # Finding the largest number already used
            self.num = 1
            while os.path.exists(mkpath(input_dir, "user_test" + str(self.num))):
                self.num += 1

            # Saving test input
            with open(mkpath(input_dir, "user_test" + str(self.num)), "w", encoding="utf-8") as test_file:
                test_file.write(input_data.strip())

            # Asking for expected test output
            sublime.active_window().show_input_panel("Expected output", "",
                                                     lambda outp: sublime.set_timeout_async(lambda: on_done_output(outp), 0),
                                                     None, None)

        def on_done_output(output_data):

            # Creating output directory
            output_dir = mkpath(working_dir, "EasyCP_" + file_name, "output")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Saving test output
            with open(mkpath(output_dir, "user_test" + str(self.num)), "w", encoding="utf-8") as test_file:
                test_file.write(output_data.strip())

            # Status message: success
            sublime.status_message("EasyCP: Test-case has been added")

        # Asking for test input
        sublime.active_window().show_input_panel("Input", "",
                                                 lambda inp: sublime.set_timeout_async(lambda: on_done_input(inp), 0),
                                                 None, None)
