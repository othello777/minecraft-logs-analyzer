import gzip
import os
import re
from csv import writer as csv_writher
from datetime import timedelta
from glob import iglob
from io import TextIOBase, SEEK_END
from pathlib import Path

import tkinter.scrolledtext as tkst
import tkinter.ttk as ttk
from tkinter import Tk, Entry, Button, StringVar, Frame, IntVar, Message, messagebox, END, filedialog
from tkinter.colorchooser import *

re._pattern_type = re.Pattern
from _thread import start_new_thread

try:
	import pyi_splash
except ModuleNotFoundError:
	print("Failed to display a splash screen.")

# I import matplotlib in the module_not_found if it is not found otherwise in the matplotlib when building the gui we will see how that goes

def read_backward_until(stream, delimiter, buf_size=32, stop_after=1, trim_start=0):
	"""
	`stream` (TextIOBase): Stream to read from
	`delimiter` (str|re._pattern_type): Delimeter marking when to stop reading
	`buf_size` (int): Number of characters to read/store in buffer while
					  progressing backwards. Ensure this is greater than or
					  equal to the intended length of `delimiter` so that the
					  entire delimiter can be detected
	`stop_after` (int): Return the result after detecting this many delimiters
	`trim_start` (int): If not 0, this many characters will be skipped
						from the beginning of the output (to return only
						what comes after delimiter, for instance)
	"""
	if not isinstance(stream, TextIOBase):
		raise TypeError('Expected type of `stream` to be TextIOBase, got %s' % type(stream))
	if not (isinstance(delimiter, str) or isinstance(delimiter, re._pattern_type)):
		raise TypeError('Expected type of `delimiter` to be str or '
		                'regex pattern, got %s' % type(delimiter))
	
	stop_after -= 1
	original_pos = stream.tell()
	cursor = stream.seek(0, SEEK_END)
	buf = ' ' * (buf_size * 2)
	
	while cursor >= 0:
		if cursor >= buf_size:
			cursor -= buf_size
		else:
			cursor = 0
		stream.seek(cursor)
		# Combine the previous two buffers in case delimiter runs
		# across two buffers
		buf = stream.read(buf_size) + buf[:buf_size]
		
		if isinstance(delimiter, str):
			delim_pos = buf.find('\n')
		else:
			delim_pos = delimiter.search(buf)
			delim_pos = delim_pos.start() if delim_pos else -1
		
		if delim_pos == -1 or delim_pos >= buf_size:
			# Skip if no delimiter found or if it's in the second half of
			# the buffer (it will turn up twice as it moves to the end of
			# the buffer)
			pass
		elif stop_after > 0:
			# Decrement since we found delimiter
			stop_after -= 1
		else:
			# Move to the start of the final line
			stream.seek(cursor + delim_pos + trim_start - 1)
			last_line = stream.read()
			stream.seek(original_pos)
			return last_line
	# No match
	return None


def read_last_line(stream):
	return read_backward_until(stream, os.linesep, stop_after=2, trim_start=2)


def iter_logs(path):
	if isinstance(path, str):
		path = Path(path)
	elif not isinstance(path, Path):
		raise TypeError('Expected type of `path` to be str or Path, got %s' % type(path))
	open_methods = {'.log': open, '.gz': gzip.open}
	
	for file in path.iterdir():
		if file.suffix not in open_methods:
			continue
		elif not file.name.startswith('20'):
			continue
		with open_methods[file.suffix](file, 'rt', encoding='ansi', errors='replace', newline='') as f:
			yield f


def count_playtime(path, count=-1, print_files='file'):
	global graph_data_collection, stop_scan, total_data_time, data_total_play_time, csv_data
	current_month = ""
	total_data_time = 0
	time_pattern = re.compile(
		r'\[(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\]', re.I
	)
	time_pattern_simple = re.compile(r'\d{2}:\d{2}:\d{2}')
	total_time = timedelta()
	
	for log in iter_logs(path):
		if stop_scan:
			stop_scan = False
			insert("\nTotal Time:" + " " + str(total_time))
			data_total_play_time = total_time
			return
		if count == 0:
			return
		count -= 1
		
		try:
			start_time = time_pattern.match(log.readline()).groupdict()
			end_time = time_pattern.match(
				read_backward_until(log, time_pattern_simple)).groupdict()
		except AttributeError as e:
			# Not a recognized chat log
			insert("ERROR: {} generated this error: {}".format(Path(log.name).name, e))
			continue
		except EOFError:
			insert('ERROR: {} may be corrupted -- skipping'.format(Path(log.name).name))
			continue
		except OSError:
			insert('ERROR: {} may be corrupted or is not gzipped -- skipping'.format(Path(log.name).name))
			continue
		except:
			insert('ERROR: An error occured while scanning file {} -- skiping')
		start_time = timedelta(
			hours=int(start_time['hour']),
			minutes=int(start_time['min']),
			seconds=int(start_time['sec'])
		)
		end_time = timedelta(
			hours=int(end_time['hour']),
			minutes=int(end_time['min']),
			seconds=int(end_time['sec'])
		)
		if end_time < start_time:
			end_time += timedelta(days=1)
		delta = end_time - start_time
		total_time += delta
		if print_files == 'full':
			insert(str(log.name) + " " + str(delta))
		elif print_files == 'file':
			insert(str(Path(log.name).name) + " " + str(delta))
		# collect data for csv
		csv_data[str(Path(log.name).name)[:12]] = str(delta)
		
		# collect data for graph
		month = str(Path(log.name).name)[:7]
		if current_month != month:  # Check if we are still on the same month if not save the current month and move on
			if current_month != '':
				if current_month not in graph_data_collection:
					graph_data_collection[current_month] = 0
				graph_data_collection[current_month] += int(total_data_time / 3600)  # make seconds an hour this will mean that if you played less then an hour it will end up as 0
			# add first month and next
			current_month = month
			total_data_time = delta.total_seconds()
		else:
			total_data_time += delta.total_seconds()
			data_total_play_time = total_time
	
	return total_time


def search_logs(pattern, return_after=-1, output_file=None):
	# if sub is not None:
	#     pattern =   r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\S+ ' \
	#               + r'\[(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\] ' \
	#               + r'\[(?P<caller>[\w ]+?/)(?P<level>[A-Z]+)\]: ' \
	#               + pattern
	pattern = re.compile(pattern, flags=re.I)
	
	try:
		out = None
		if output_file:
			out = open(output_file, 'wt', encoding='utf_8')
		
		for log in iter_logs():
			for line in log:
				search = re.search(pattern, line)
				if search:
					return_after -= 1
					# Set what will be output
					if pattern.groups != 0:
						# There is a capturing group in the pattern regex;
						# use the first one available
						to_output = search.group(1)
					else:
						to_output = line
					
					if out:
						# Write to file
						out.write(to_output)
					else:
						insert(str(to_output))
				
				if return_after == 0:
					return
	finally:
		if out:
			out.close()


def insert(string_input, newline=True, error=False, scroll=True):  # to get text to output field
	string_input = str(string_input)
	if error == True:
		text.insert(END, "** ")
		text.insert(END, string_input.upper())
		text.insert(END, " **")
	if error == False:
		text.insert(END, string_input)
	if newline == True:
		text.insert(END, "\n")
	if scroll:
		text.see(END)
	return


def change_mode():
	global scan_mode
	scan_mode = mode.get()
	if scan_mode == 1:
		pathInput.config(state='disabled', cursor="arrow")
	else:
		pathInput.config(state='normal', cursor="hand2")
	insert("Changed mode to " + mode_dict[scan_mode])


# probably put path detect here


data_total_play_time = 0


def count_playtimes_tread(paths, mode):
	global data_total_play_time
	total_time = timedelta()
	if mode == 1:
		paths = Path(paths)
		total_time += count_playtime(paths, print_files='file')
	if mode == 2:
		for path in paths:
			total_time += count_playtime(path, print_files='full' if len(paths) > 1 else 'file')
	if mode == 3:
		for path in paths:
			if path.is_dir():
				total_time += count_playtime(path, print_files='full')
	insert("\nTotal Time:" + " " + str(total_time))
	data_total_play_time = total_time


def run():
	global graph_data_collection, csv_data
	csv_data = {}
	graph_data_collection = {}
	insert("Starting log scanning...")
	if scan_mode == 0:  # no input clicked yet
		insert("No mode selected, please select mode!")
		return
	elif scan_mode == 1:
		default_logs_path = Path('C:/Users', os.getlogin(), 'AppData/Roaming/.minecraft', 'logs')
		if default_logs_path.exists():
			
			start_new_thread(count_playtimes_tread, tuple(), {"paths": default_logs_path, "mode": scan_mode})
			return
		# say that it did not exist
		else:
			insert("ERROR: Could not automatically locate your .minecraft/logs folder")
	
	elif scan_mode == 2:  # files
		paths_list = pathInput.get().split("|")
		for path in paths_list:
			path = Path(path)
			if path.exists() == False:
				insert("ERROR: One of your specified paths does not exit:")
				insert(path, error=True)
				return
		paths_list_ready = [Path(path) for path in paths_list]
		start_new_thread(count_playtimes_tread, tuple(), {"paths": paths_list_ready, "mode": scan_mode})
	
	
	elif scan_mode == 3:  # glob
		globs = pathInput.get().split("|")
		glob_list = []
		for _glob in globs:
			for paths in iglob(_glob + "", recursive=True):
				glob_list.append(Path(paths))
		for path in glob_list:
			if path.exists() == False:
				insert("ERROR: One of your specified paths does not exit:")
				insert(str(path), error=True)
				return
		
		start_new_thread(count_playtimes_tread, tuple(), {"paths": glob_list, "mode": scan_mode})


def exit():
	global stop_scan
	stop_scan = True
	insert("Stopping scan...")
	return


def create_graph():
	global plt
	try:
		if graph_data_collection == {}:
			insert("Not enough data to create a graph, one full month is needed")
			return
		data_list_dates = [dates for dates in graph_data_collection]
		data_list_hour = [hours[1] for hours in graph_data_collection.items()]
		data_list_dates, data_list_hour = zip(*sorted(zip(data_list_dates, data_list_hour)))
		plt.bar(data_list_dates, data_list_hour, color=graph_color)
		
		plt.xticks(rotation='vertical')
		
		plt.xlabel("Months")
		plt.ylabel("Hours")
		plt.title("Total playtime:\n" + str(data_total_play_time))
		plt.draw()
		plt.show()
	except Exception as E:
		insert("An error ocured while creating the graph: " + str(E), error=True)
		insert("Try closing and opening the program\nMake sure that you have matplotlib installed!")


def module_not_found():
	global plt
	if messagebox.askokcancel("Could not import Matplotlib module", 'It looks like you do not have the matplotlib module installed\nWithout this module you can not make graphs\nInputing *pip install matplotlib* into the cmd will install it\n\nYou can also auto install by clicking ok. This will run os.system("pip install --user matplotlib")'):
		insert("Attempting to install matplotlib + dependencies. This may take some time...")
		os.system("pip install --user matplotlib")
	try:
		from matplotlib import pyplot as plt
		
		insert("Succesfully installed matplotlib!")
	except ModuleNotFoundError:
		insert("matplotlib can still not be imported")
	except Exception as error:
		insert("Something may have gone wrong " + str(error))


def getColor():
	global graph_color
	color = askcolor()
	graph_color = color[1]
	colorButton.config(bg=graph_color)
	if graph_color is not None:
		insert(f"Color changed to {graph_color}")


def create_csv():
	if len(csv_data) != 0:
		filename = filedialog.asksaveasfilename(initialdir="/desktop", title="Save file:", initialfile="minecraft_playtime.csv",
		                                        filetypes=(("csv files", "*.csv"), ("all files", "*.*")))
		with open(filename, newline='', mode="w+") as csvfile:
			writer = csv_writher(csvfile, delimiter=',')
			writer.writerow(["Day", "Hours"])
			writer.writerows(csv_data.items())
	else:
		insert("Not enough data to create a csv file, make sure to start a scan first")


if __name__ == '__main__':
	background_color = "#23272A"
	outline_color = "#2C2F33"
	fg_color = "white"
	csv_data = {}
	root = Tk()
	
	graph_data_collection = {}
	stop_scan = False
	try:
		from matplotlib import pyplot as plt
	except ImportError:
		plt = 0
		start_new_thread(module_not_found, ())
	
	# here the gui stuff starts
	frame = Frame(root, bg=background_color)
	frame.pack()
	
	root.title("Playtime calculator - By Quinten Cabo")
	root.config(bg=background_color)
	
	# mode selection
	modeText = Message(frame, text="Choose scan mode:", bg=background_color, fg=fg_color, relief="groove", font="Helvetica 10")
	modeText.config(width=120)
	modeText.pack()
	
	mode_dict = {
		1: "Automatic",
		2: "Manual path",
		3: "Glob"
	}
	
	s = ttk.Style()  # Creating style element
	s.configure('Wild.TRadiobutton',  # First argument is the name of style. Needs to end with: .TRadiobutton
	            background=background_color,  # Setting background to our specified color above
	            foreground=fg_color, font="Helvetica 10")  # You can define colors like this also
	
	mode = IntVar(None, 1)
	mode1 = ttk.Radiobutton(frame, variable=mode, text="Automatic    ", value=1, command=change_mode, cursor="hand2", style='Wild.TRadiobutton')
	mode1.pack()
	mode2 = ttk.Radiobutton(frame, variable=mode, text="Enter path(s)", value=2, command=change_mode, cursor="hand2", style='Wild.TRadiobutton')
	mode2.pack()
	mode3 = ttk.Radiobutton(frame, variable=mode, text="Enter glob    ", value=3, command=change_mode, cursor="hand2", style='Wild.TRadiobutton')
	mode3.pack()
	scan_mode = mode.get()
	
	Message(frame, text="", bg="#23272A").pack()
	
	# Path input
	pathText = Message(frame, text="(Sperate input with '|')\nEnter path(s)/glob:", bg=background_color, fg=fg_color, relief="groove", font="Helvetica 10")
	pathText.config(width=130, justify="center")
	pathText.pack()
	
	pathInput = StringVar()
	pathInput = Entry(frame, exportselection=0, textvariable=pathInput, state="disabled", cursor="arrow", bg="white", width=40, disabledbackground=background_color, font="Helvetica 10")
	pathInput.pack()
	
	Message(frame, text="", bg=background_color).pack()
	
	# run button
	submitButton = Button(frame, text="Run", command=run, cursor="hand2", bg=background_color, fg=fg_color, font="Helvetica 10")
	submitButton.config(width=20)
	submitButton.pack()
	
	# graph button
	graphButton = Button(frame, text="Create graph", command=create_graph, cursor="hand2", bg=background_color,
	                     fg=fg_color, font="Helvetica 10")
	graphButton.config(width=20)
	graphButton.pack()
	
	graph_color = "#18aaff"
	
	colorButton = Button(frame, text='Select Color', command=getColor, bg=graph_color, font="Helvetica 10")
	colorButton.config(width=20)
	colorButton.pack()
	
	# csv button
	graphButton = Button(frame, text="Export as csv", command=create_csv, cursor="hand2", bg=background_color, fg=fg_color, font="Helvetica 10")
	graphButton.config(width=20)
	graphButton.pack()
	
	# output
	text = tkst.ScrolledText(frame, background="#2C2F33", fg="white", font="Helvetica 11")
	text.config(width=120)
	text.pack()
	
	# exit button
	stopButton = Button(frame, text="Stop scanning", command=exit, width=20, bg=background_color, fg=fg_color, font="Helvetica 10")
	stopButton.pack()
	
	if os.path.exists("icon.ico"):
		root.iconbitmap("icon.ico")
	else:
		print("Could not find icon.ico so using default tkinter icon")
	
	
	# Close the splash screen. It does not matter when the call
	# to this function is made, the splash screen remains open until
	# this function is called or the Python program is terminated.
	try:
		pyi_splash.close()
	except:
		pass
	
	root.mainloop()
