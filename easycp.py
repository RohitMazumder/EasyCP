
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

url=''


class EasycpCommand(sublime_plugin.TextCommand):

	SAMPLE_INPUT='in'
	SAMPLE_OUTPUT='out'

	def run(self, edit):

		self.window = self.view.window()
		vars = self.window.extract_variables()

		try:
			file_extension = vars['file_extension']
			file_name = vars['file_base_name']
			file = vars['file']
			working_dir = vars['file_path']
			classpath = working_dir
		except KeyError:
			sublime.error_message('Please save your file before continuing ')
			raise

		assert file_extension == 'java',sublime.error_message('.'+file_extension + ' extension is not supported')

		def compare_output(out_dir, myout_dir):


			for i in range(1,self.num_tests):

				print("****************Executing Test-Case {}****************\n".format(i))

				out_file = os.path.join(out_dir,'out'+str(i))
				myout_file = os.path.join(myout_dir,'in'+str(i))
				f2 = open(myout_file,"r")
				f1 = open(out_file,"r")

				
				for line1, line2 in itertools.zip_longest(f1, f2):
					
					if line1!=None and line2!=None:
						if line1.strip() and line2.strip() and line1!=line2:
							sublime.error_message("Problem in sample test-case {}\n".format(i))
							break
					elif ((line1==None and line2!=None and line2.strip()) 
						or (line2==None and line1!=None and line1.strip())):
						sublime.error_message("Problem in sample test-case {}\n".format(i))
						break

				f1.close()
				f2.close()


		def get_output(java_file,in_dir,myout_dir):
			#Compiles the java_file, executes and stores the
			#output corresponding to every input file in the in_dir 
			#directory, with the same name as that of the input file 
			#in the myout_dir


			subprocess.check_call(['javac', java_file])
			for i in os.listdir(in_dir):
				in_file = open(os.path.join(in_dir,i)) 
				out_file = open(os.path.join(myout_dir,i),"w")
				cmd = ['java','-cp',classpath,file_name]
				subprocess.call(cmd, stdin = in_file, stdout = out_file)
				in_file.close()
				out_file.close()

		
		def parse_url(url,input_fp,output_fp):
			html = urlopen(url).read()
			parser = cfparser.CFParser(input_fp,output_fp)
			parser.feed(html.decode('utf-8'))
			self.num_tests = parser.get_num_tests()

		def submit(url):
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
			get_output(file,input_fp,myoutput_fp)
			compare_output(output_fp,myoutput_fp)




		sublime.active_window().show_input_panel(
			"Insert URL", url, submit, None, None)

