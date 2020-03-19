
import sublime
import sublime_plugin

from . import cfparser
import os
import subprocess
try:
	from urllib2 import urlopen
except:
	from urllib.request import urlopen
import itertools
import threading

url=''
	
class Environment(sublime_plugin.TextCommand):

	def __init__(self,view):
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

		return self.file_extension,self.file_name,self.file,self.working_dir,self.classpath

class EasycpCommand(Environment):

	SAMPLE_INPUT='in'
	SAMPLE_OUTPUT='out'

	def run(self, edit):
		
		self.view.run_command("compile")
		self.view.run_command("run")
		
class RunCommand(Environment):

	panel = None
	panel_lock = threading.Lock()


	def run(self, edit):

		file_extension, file_name, file, working_dir, classpath = self.get_variables()

		def get_num_tests():

			self.input_dir = os.path.join(working_dir,file_name,'input')
			self.output_dir = os.path.join(working_dir,file_name,'output')
			self.myout_dir = os.path.join(working_dir,file_name, 'myoutput')
			try:
				self.num_tests = len(os.listdir(self.input_dir))
			except FileNotFoundError:
				sublime.error_message('You must parse the test-cases first')
				raise
			return self.num_tests

		def get_output():

			for i in range(1,self.num_tests+1):
				in_file = open(os.path.join(self.input_dir,'in'+str(i))) 
				out_file = open(os.path.join(self.myout_dir,'out'+str(i)),"w")
				cmd = ['java','-cp',classpath,file_name]
				subprocess.call(cmd, stdin = in_file, stdout = out_file)
				in_file.close()
				out_file.close()

		def display_output():

			msg=''
			for i in range(1, self.num_tests+1):
				msg += "************Executing Test-Case {}************\n".format(i)
				in_file = os.path.join(self.input_dir,'in'+str(i))
				out_file = os.path.join(self.output_dir,'out'+str(i))
				myout_file = os.path.join(self.myout_dir,'out'+str(i))
				f1 = open(in_file,"r")
				f2 = open(out_file,"r")				
				f3 = open(myout_file,"r")
				msg += "Input:\n"
				msg += f1.read()
				msg += "Expected Output:\n"
				msg += f2.read()
				msg += "Your Output:\n"
				msg += f3.read()
				msg += "Status :{}\n".format(compare_output(out_file, myout_file))

			#sublime.message_dialog(msg)
			with self.panel_lock:

				self.panel = self.window.create_output_panel('panel')
				self.panel.set_read_only(False)
				self.panel.run_command("append", {"characters": msg})
				self.panel.set_read_only(True)
				self.window.run_command('show_panel', {"panel":"output.panel"})

			#print(msg)





		def compare_output(out_file, myout_file):
		###TODO: Make it more user-friendly	

			f2 = open(myout_file,"r")
			f1 = open(out_file,"r")

			for line1, line2 in itertools.zip_longest(f1, f2):
				
				if line1!=None and line2!=None:
					if line1.strip() and line2.strip() and line1!=line2:
						return "FAILED"
				elif ((line1==None and line2!=None) 
					or (line2==None and line1!=None)):
					return "FAILED"

			f1.close()
			f2.close()
			return "Passed Successfuly"

		self.num_tests = get_num_tests()
		get_output()
		display_output()
		

class CompileCommand(Environment):
###TODO: Display the compile time error message to the users

	def run(self, edit):

		file_extension, file_name, file, working_dir, classpath = self.get_variables()
		assert file_extension == 'java',sublime.error_message('.'+file_extension + ' extension is not supported')

		try:	
			val = subprocess.check_call(['javac', file],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		except subprocess.CalledProcessError:
			sublime.error_message("Compilation failed : Returned non-zero exit status")
			raise


class ParseUrlCommand(Environment):

	def run(self,edit):

		file_extension, file_name, file, working_dir, classpath = self.get_variables()

		def on_done(url):
			#Create new directory structure to store sample input,
			#sample output and output generated my user's code

			input_fp = os.path.join(working_dir,file_name,'input')
			if	not os.path.exists(input_fp):
				os.makedirs(input_fp)
			output_fp = os.path.join(working_dir,file_name,'output')
			if	not os.path.exists(output_fp):
				os.makedirs(output_fp)
			myoutput_fp = os.path.join(working_dir,file_name,'myoutput')
			if	not os.path.exists(myoutput_fp):
				os.makedirs(myoutput_fp)
			parse_url(url,input_fp,output_fp)

		def parse_url(url,input_fp,output_fp):
			#Parses test cases

			html = urlopen(url).read()
			parser = cfparser.CFParser(input_fp,output_fp)
			parser.feed(html.decode('utf-8'))

		sublime.active_window().show_input_panel(
			"Insert URL", url, on_done, None, None)



