
try:
	from HTMLParser import HTMLParser
except:
	from html.parser import HTMLParser

SAMPLE_INPUT='in'
SAMPLE_OUTPUT='out'
MY_OUTPUT='myout'

class CFParser(HTMLParser):
#Scraps the html document and stores the sample inputs 
#inside in_folder as in1, in2,...so on.
#Similarly, it scraps the sample outputs corresponding to each
#sample input and stores them inside out_folder 
#as out1, out2, ... so on.


	def __init__(self, in_folder, out_folder):
		HTMLParser.__init__(self)
		self.in_folder = in_folder
		self.out_folder = out_folder
		self.num_tests = 0
		self.testfile = None
		self.start_copy = False

	def handle_starttag(self, tag, attrs):
		if tag == 'div':
			if attrs == [('class', 'input')]:
				self.num_tests += 1
				self.testfile = open('%s/%s%d' % (self.in_folder, SAMPLE_INPUT, self.num_tests), 'wb')
			elif attrs == [('class', 'output')]:
				self.testfile = open('%s/%s%d' % (self.out_folder, SAMPLE_OUTPUT, self.num_tests), 'wb')
		elif tag == 'pre':
			if self.testfile != None:
				self.start_copy = True

	def handle_endtag(self, tag):
		if tag == 'br':
			if self.start_copy:
				self.testfile.write('\n'.encode('utf-8'))
				self.end_line = True
		if tag == 'pre':
			if self.start_copy:
				if not self.end_line:
					self.testfile.write('\n'.encode('utf-8'))
				self.testfile.close()
				self.testfile = None
				self.start_copy = False

	def handle_entityref(self, name):
		if self.start_copy:
			self.testfile.write(self.unescape(('&%s;' % name)).encode('utf-8'))

	def handle_data(self, data):
		if self.start_copy:
			self.testfile.write(data.strip('\n').encode('utf-8'))
			self.end_line = False

	