from tkinter import *
from tkinter import ttk
from tkinter.ttk import Separator, Notebook, Combobox
from tkinter.ttk import Button as TButton
from tkinter.filedialog import askopenfilename
import tkinter.scrolledtext as scrolledtext
import tkinter as tk
from tkinter import messagebox
import threading
import time
import donutstest
import queue
from threading import Timer
import ctypes
import os

import sys

import SystemManager
import ConnDialog
import TargetDialog
import CalibrationSettings
import CalibrationProcedure
import telctrl
import libsbig
import argoterm


import serial
#from serial import VERSION as SER_VERSION

VERSION = 3

# constants
CORE_UPDATE_TICK = 100
UI_FONT_SIZE = 12


LICENSE_TEXT = "\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" + \
    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS\n" + \
    "FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR\n" + \
    "COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER\n" + \
    "IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN\n" + \
    "CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n" + \
    "\nYou must AGREE to the above terms to continue using this software."

class MainFrame(Frame):
    def __init__(self, master):
        Frame.__init__(self, master)
        self.master = master
        self.master.title("NuDomeTracker 0.1")
        self.master.geometry("1024x600+200+200")
        self.master.protocol("WM_DELETE_WINDOW", self._on_closing)
        # control panel vars
        # button states        
        self.DIR_STATE =     0b0000
        self.FOCUS_STATE =   0b00
        self.ROTATE_STATE =  0b00
        self.SHUTTER_STATE = 0b00
#========================================================================================================#
#------------------------- ANNA CALIBRATION STUFF - CALIBRATION THREADING QUEUE -------------------------#
#========================================================================================================#        
        # queue for calibration thread
        self.queue = queue.Queue()
        # Indicator that calibration should proceed
        self.showmustgoon = False
        # How many times was calibration called (we don't want to start 100500 calibration threads)
        self.pressedstartcount = 0
        # Indicator that it's a repeated calibration at interval
        self.IntervalCalibration = False
        # Indicator that it's a repeated calibration at interval for specific duration
        self.DurationCalibration = False
        # Indicator that tracking is on
        self.tracking = IntVar()
        # Indicator that jogging is on
        self.jog = IntVar()
        # Label for Progress Bar
        self.pglbl = "Calibration Progress"
        self.telmover = telctrl.TelescopeInterface(('COM5', 'COM6'))
        self.telmover.disconnect()
        # Speed Choice
        self.velocity = StringVar()
        # Argo Stuff
        self.argo =  None
        self.toggleArgo = 0
#--------------------------------------------------------------------------------------------------------#
#========================================================================================================#  
        # testing crap
        self.test_coast = 0        
        self.pack(fill=BOTH, expand=1)        
        self._initWidgets()
        self.SystemCore = SystemManager.SystemCore(self)        
        # start control panel instance
        #self.ConnectionsPanel = ConnDialog.ConnectionsPanel(self)
        #self.ControlPanel = ControlPanel(self)
        self.platform = None
        self.DetectPlatform()        
        self.LockUI(1, True)        
        self._update()
     
    
    def DetectPlatform(self):
        if sys.platform.startswith('win'):
            self.platform = 'win'
        elif sys.platform.startswith('linux'):
            self.platform = 'linux'
        else:
            raise EnvironmentError('Unsupported platform')

    #def ShowConnectionsPanel(self, event=None):
    #    self.ConnectionsPanel.deiconify()
    #    self.ConnectionsPanel.update()
    #    self.ConnectionsPanel.focus_set()

 
    def LockUI(self, group=0, state=False):        
        if state == False:
            state = DISABLED
        elif state == True:
            state = NORMAL        
        if group == 1: # telescope control
            self.tel_north['state'] = state
            self.tel_east['state'] = state
            self.tel_west['state'] = state
            self.tel_south['state'] = state
        elif group == 2:
            self.tel_east['state'] = state
            self.tel_west['state'] = state
        elif group == 3:
            self.tel_north['state'] = state
            self.tel_south['state'] = state
    
    def CheckCoasting(self):
        # must check motion states of the motors        
        self.test_coast += 1
        self.LockUI(1, DISABLED)        
        if self.test_coast > 3:
            self.test_coast = 0
            print("stopped coasting")
            if self.SystemCore._ra_connected and not self.SystemCore._dec_connected:
                self.LockUI(2, NORMAL)
            elif not self.SystemCore._ra_connected and self.SystemCore._dec_connected:
                self.LockUI(3, NORMAL)
            elif self.SystemCore._ra_connected and self.SystemCore._dec_connected:
                self.LockUI(1, NORMAL)                
        else:
            self.after(50, self.CheckCoasting)
        
    def CheckButtonStates(self, event=None):
        if (self.DIR_STATE & 0b1111): 
            print("dir change")        
        self.after(200, self.CheckButtonStates)
    
    def SouthDown(self, event=None):
        self.telmover.connect()
        v = float(self.velocity.get())
        print(v)
        self.telmover.move_south(v)
        self.telmover.disconnect()
##        if ~(self.DIR_STATE & 0b1111) and self.SystemCore._dec_connected:
##            self.DIR_STATE = 0b0001
##            self.SystemCore.StartMoveSouth()
    
    def NorthDown(self, event=None):
        self.telmover.connect()
        v = float(self.velocity.get())
        print(v)
        self.telmover.move_north(v)
        self.telmover.disconnect()
##        if ~(self.DIR_STATE & 0b1111) and self.SystemCore._dec_connected:
##            self.DIR_STATE = 0b0010
##            self.SystemCore.StartMoveNorth()
    
    def EastDown(self, event=None):
        self.telmover.connect()
        v = float(self.velocity.get())
        print(v)
        self.telmover.move_east(v)
        self.telmover.disconnect()
##        if ~(self.DIR_STATE & 0b1111) and self.SystemCore._ra_connected:
##            self.DIR_STATE = 0b0100
##            self.SystemCore.StartMoveEast()
    
    def WestDown(self, event=None):
        self.telmover.connect()
        v = float(self.velocity.get())
        print(v)
        self.telmover.move_west(v)
        self.telmover.disconnect()
##        if ~(self.DIR_STATE & 0b1111) and self.SystemCore._ra_connected:
##            self.DIR_STATE = 0b1000
##            self.SystemCore.StartMoveWest()

    def TrackSky(self, event=None):        
        if self.tracking.get()==1:
            print('Tracking')
            self.telmover.connect()
            self.telmover.start_tracking()
            self.telmover.disconnect()
        if self.tracking.get()==0:
            print('Not Tracking')
            self.telmover.connect()
            self.telmover.stop_tracking()
            self.telmover.disconnect()

    def StartJogging(self, event=None):
        if self.jog.get()==1:
            print('Jogging')
            print('How is jogging different from motion during calibration procedure? Do controls need to be disabled')
        if self.jog.get()==0:
            print('Not Jogging')

    def DirUp(self, event=None):
        self.telmover.connect()
        self.telmover.stop_move('ra')
        self.telmover.stop_move('dec')
        self.telmover.disconnect()
##        if (self.DIR_STATE & 0b1111):
##            self.DIR_STATE = 0b0000
##            self.CheckCoasting()
        
    def ProcessInput(self, event=None):
        print('called')        
        if (self.DIR_STATE & 0b1111):
            print(True)
        else:
            print(False)
    
    def ShowControlPanel(self):
        #self.ControlPanel.deiconify()
        #self.ControlPanel.update()
        pass
    
    #def ShowConnections(self):
    #    self.ConnectionsPanel.deiconify()
    #    self.ConnectionsPanel.update()
    
    def connect_hardware(self):
        self._write_message("Starting peripheral connection sequence ...\n")
        if self.SystemCore.ConnectAllDevices() != False:
            self._write_message("\n\nok.\n")
        else:
            self._write_message("error!\n")
    
    def load_macro(self):
        # get filename
        filename = askopenfilename(initialdir=".", filetypes =(("NuDomeTracker Macros", "*.dtm"),
            ("All Files","*.*")), title = "Select macro file")
        # open file on your own
        if filename:
            self.SystemCore.set_macro(filename)
            
    def _exit(self):
        self.master.destroy()
    
    def _update(self):
        # update system internal time and poll sensors
        self.SystemCore.tick()
        # make sure everything is active        
        # get local time
        lt_hour = self.SystemCore._observatory.local_time.hour
        lt_min = self.SystemCore._observatory.local_time.minute
        lt_sec = self.SystemCore._observatory.local_time.second
        ut_hour = self.SystemCore._observatory.universal_time.hour
        ut_min = self.SystemCore._observatory.universal_time.minute
        ut_sec = self.SystemCore._observatory.universal_time.second        
        lmst_hour = self.SystemCore._observatory.lms_time[0]
        lmst_min = self.SystemCore._observatory.lms_time[1]
        lmst_sec = self.SystemCore._observatory.lms_time[2]        
        self.local_time['text'] = "{0:02d}:{1:02d}:{2:02d}".format(lt_hour, lt_min, lt_sec)
        self.utc_time['text'] = "{0:02d}:{1:02d}:{2:02d}".format(ut_hour, ut_min, ut_sec)
        self.lms_time['text'] = "{0:02d}:{1:02d}:{2:02d}".format(lmst_hour, lmst_min, lmst_sec)
        if self.SystemCore._target_object is not None:
            h, m, s = self.SystemCore._target_object.ra
            self.trg_RA_disp['text'] = "{0:02d}h {1:02d}m {2:02d}s".format(
                int(h), int(m), int(s))
            d, m, s = self.SystemCore._target_object.dec
            self.trg_DEC_disp['text'] = "{0:+03d}d {1:02d}m {2:02d}s".format(
                int(d), int(m), int(s))
            h, m, s = self.SystemCore._target_object.hour_angle()
            self.trg_HA_disp['text'] = "{0:+03d}h {1:02d}m {2:02d}s".format(
                int(h), int(m), int(s))
        h, m, s = self.SystemCore._telescope_coord.ra
        self.RA_disp['text'] = "{0:02d}h {1:02d}m {2:02d}s".format(
            int(h), int(m), int(s))
        d, m, s = self.SystemCore._telescope_coord.dec
        self.DEC_disp['text'] = "{0:+03d}d {1:02d}m {2:02d}s".format(
            int(d), int(m), int(s))
        h, m, s = self.SystemCore._telescope_coord.hour_angle()
        self.HA_disp['text'] = "{0:+03d}h {1:02d}m {2:02d}s".format(
            int(h), int(m), int(s))
        # reset for next tick
        self.master.after(CORE_UPDATE_TICK, self._update)
    
    def _write_message(self, msg='\n', scroll=True):
        # write a message to the message window
        self.message_window.config(state=NORMAL)
        self.message_window.insert(END, str(msg))        
        if scroll: 
            self.message_window.see(END) # scroll to bottom            
        self.message_window.config(state=DISABLED)
    
    def _initMenus(self):
        # Create main menu bar
        menu_bar = Menu(self.master)
        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Quit", command=self._on_closing)
        # Add the "File" drop down sub-menu in the main menu bar
        menu_bar.add_cascade(label="File", menu=file_menu)
        # devices menu
        devices_menu = Menu(menu_bar, tearoff=0)
        devices_menu.add_checkbutton(label="Connect Argo", variable=self.toggleArgo, onvalue=1, offvalue=0, command=self.connect_argo_navis)
        menu_bar.add_cascade(label="Peripherals", menu=devices_menu)
        # guidance menu
        guidance_menu = Menu(menu_bar, tearoff=0)
        guidance_menu.add_command(label="Set target object ...", command=None)
        menu_bar.add_cascade(label="Guidance", menu=guidance_menu)
        # macro menu
        macro_menu = Menu(menu_bar, tearoff=0)
        macro_menu.add_command(label="Load", command=None)
        menu_bar.add_cascade(label="Macro", menu=macro_menu)
        # tools menu
        tools_menu = Menu(menu_bar, tearoff=0)
        tools_menu.add_command(label="Nothing here yet.", command=None)
        menu_bar.add_cascade(label="Tools", menu=tools_menu)        
        self.master.config(menu=menu_bar)
    
    def _initToolbar(self):
        tool_bar = Frame(self, relief=RAISED, border=1)
        tool_bar.pack(fill=X, expand=0, side=TOP)
        # Created
        photo = PhotoImage(file="stock_connect.gif")
        self.tb_connect = Button(tool_bar, text="Connect", image=photo, relief=FLAT, compound=TOP, border=1,
            command=self.connect_hardware)
        self.tb_connect.image = photo
        self.tb_connect.pack(side=LEFT, padx=3, pady=5)        
        Separator(tool_bar, orient=VERTICAL).pack(fill=Y, side=LEFT, padx=2, pady=8)
        # Created
        photo = PhotoImage(file="gnome-joystick.gif")
        self.tb_control = Button(tool_bar, text="Remote", image=photo, relief=FLAT,
            compound=TOP, command=self.ShowControlPanel, border=1)
        self.tb_control.image = photo
        self.tb_control.pack(side=LEFT, padx=3, pady=5)
        # Created
        photo = PhotoImage(file="stock_hyperlink-target.gif")
        self.tb_control = Button(tool_bar, text="Target", image=photo, relief=FLAT,
            compound=TOP, command=self._on_set_target, border=1)
        self.tb_control.image = photo
        self.tb_control.pack(side=LEFT, padx=3, pady=5)
#========================================================================================================#
#------------------------- ANNA CALIBRATION STUFF - CALIBRATION SETTINGS BUTTON -------------------------#
#========================================================================================================#
        photo = PhotoImage(file="Calibration.gif")
        self.Calibration = Button(tool_bar, text="Calibration", image=photo, relief=FLAT,
            compound=TOP, command=self._on_calibration_selection, border=1)
        self.Calibration.image = photo
        self.Calibration.pack(side=LEFT, padx=3, pady=5)
#--------------------------------------------------------------------------------------------------------#
#========================================================================================================#
        Separator(tool_bar, orient=VERTICAL).pack(fill=Y, side=LEFT, padx=2, pady=8)
        # Created
        photo = PhotoImage(file="stock_script.gif")
        self.tb_control = Button(tool_bar, text="Load Macro", image=photo, relief=FLAT,
            compound=TOP, command=self.load_macro, border=1)
        self.tb_control.image = photo
        self.tb_control.pack(side=LEFT, padx=3, pady=5)
        Separator(tool_bar, orient=VERTICAL).pack(fill=Y, side=LEFT, padx=2, pady=8)
#========================================================================================================#
#--------------------------- ANNA CALIBRATION STUFF - CALIBRATION PROGRESS BAR --------------------------#
#========================================================================================================#
        calibration = Frame(tool_bar)
        calibration.pack(side=LEFT)
        w = Label(calibration, text=self.pglbl)
        w.pack(side=TOP)
        self.progressbar = ttk.Progressbar(calibration, orient='horizontal', length=300, mode='determinate')
        self.progressbar.pack(side=BOTTOM, padx=3)
        # Start Button
        photo = PhotoImage(file="media-playback-start.png")
        self.startthread = Button(tool_bar, text="Start", image=photo, relief=FLAT,
            compound=TOP, command=self.starttheshow, border=1)
        self.startthread.image = photo
        self.startthread.pack(side=LEFT, padx=3, pady=5)
##        # Pause Button
##        photo = PhotoImage(file="media-playback-pause.png")
##        self.pausethread = Button(tool_bar, text="Pause", image=photo, relief=FLAT,
##            compound=TOP, command=self.pausetheshow, border=1)
##        self.pausethread.image = photo
##        self.pausethread.pack(side=LEFT)
        # Kill Button
        photo = PhotoImage(file="media-playback-stop.png")
        self.killthread = Button(tool_bar, text="Stop", image=photo, relief=FLAT,
            compound=TOP, command=self.stopbuttonpress, border=1)
        self.killthread.image = photo
        self.killthread.pack(side=LEFT, padx=3, pady=5)
##        # listbox
##        self.listbox = tk.Listbox(self, width=10, height=5)
##        self.listbox.pack(side=LEFT)
##        self.pausethread.config(state="disabled")
        self.startthread.config(state="normal")
        self.killthread.config(state="disabled")
#--------------------------------------------------------------------------------------------------------#
#========================================================================================================#
        # Created        
        photo = PhotoImage(file="stock_exit.gif")
        self.tb_quit = Button(tool_bar, text="Exit", 
            image=photo, relief=FLAT, compound=TOP, command=self._on_closing, border=1)
        self.tb_quit.image = photo
        self.tb_quit.pack(side=RIGHT, padx=5, pady=8)
       
    def _initWidgets(self):
        self._initMenus()
        self._initToolbar()        
        main_frame = Frame(self, background='black')        
        # left information panel
        left_panel = Frame(main_frame, relief=RAISED, border=1)        
        slew_frame = LabelFrame(left_panel, text=" Telescope Motion ")        
        self.tel_north = Button(slew_frame, text="North", border=1, 
            repeatinterval=250, repeatdelay=100)
        self.tel_north.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=E+W+N+S)
        self.tel_north.bind("<Button-1>", self.NorthDown)
        self.tel_north.bind("<ButtonRelease-1>", self.DirUp)        
        self.tel_west = Button(slew_frame, text="West", border=1, 
            repeatinterval=250, repeatdelay=100)
        self.tel_west.grid(row=1, column=0, columnspan=2, padx=(5,0), pady=(0,5), sticky=E+W+N+S)
        self.tel_west.bind("<Button-1>", self.WestDown)
        self.tel_west.bind("<ButtonRelease-1>", self.DirUp)
        self.tel_east = Button(slew_frame, text="East", border=1, 
            repeatinterval=250, repeatdelay=100)
        self.tel_east.grid(row=1, column=2, columnspan=2, padx=5, pady=(0,5), sticky=E+W+N+S)
        self.tel_east.bind("<Button-1>", self.EastDown)
        self.tel_east.bind("<ButtonRelease-1>", self.DirUp)
        self.tel_south = Button(slew_frame, text="South", border=1, 
            repeatinterval=250, repeatdelay=100)
        self.tel_south.grid(row=2, column=1, columnspan=2, padx=5, pady=(0,5), sticky=E+W+N+S)
        self.tel_south.bind("<Button-1>", self.SouthDown)
        self.tel_south.bind("<ButtonRelease-1>", self.DirUp)
#========================================================================================================#
#-------------------- ANNA CALIBRATION STUFF - TRACK SKY IMPLEMENTED FOR CALIBRATION --------------------#
#========================================================================================================#
        self.c = Checkbutton(slew_frame, text="Track sky", variable = self.tracking, command = self.TrackSky)
        self.c.grid(row=3, column=0, columnspan=4, padx=0, pady=(0,0), sticky=W)
#--------------------------------------------------------------------------------------------------------#
#========================================================================================================#
#========================================================================================================#
#----------------------------------- ANNA STUFF - JOGGING IMPLEMENTED  ----------------------------------#
#========================================================================================================#
        self.jogging = Checkbutton(slew_frame, text="Jogging", variable = self.jog, command = self.StartJogging)
        self.jogging.grid(row=4, column=0, columnspan=4, padx=0, pady=(0,0), sticky=W)
#--------------------------------------------------------------------------------------------------------#
#========================================================================================================#
        #close_button = Button(shutter_frame, text=" Close ")
        #close_button.pack(fill=BOTH, expand=1, side=RIGHT, padx=(0,5), pady=5)
        slew_frame.grid_rowconfigure(0, weight=1)
        slew_frame.grid_rowconfigure(1, weight=1)
        slew_frame.grid_rowconfigure(2, weight=1)
        slew_frame.grid_columnconfigure(0, weight=1)
        slew_frame.grid_columnconfigure(1, weight=1)
        slew_frame.grid_columnconfigure(2, weight=1)
        slew_frame.grid_columnconfigure(3, weight=1)        
        slew_frame.pack(fill=BOTH, expand=0, side=TOP, padx=5, pady=(0,5))        
        rate_frame = LabelFrame(left_panel, text=" Telescope Speed ")        
    
#========================================================================================================#
#--------------------------------------- ANNA STUFF - SPEED FIXED  --------------------------------------#
#========================================================================================================#        
        #Radiobutton(rate_frame, text="Ludacrous", variable=v, value=1).pack(anchor=W)
        self.speed_high = Radiobutton(rate_frame, text="Slew (Fast)", variable=self.velocity, value='5.2')
        self.speed_high.pack(anchor=W)
        self.speed_medium = Radiobutton(rate_frame, text="Guide (Medium)", variable=self.velocity, value='0.25')
        self.speed_medium.pack(anchor=W)
        self.speed_medium.select()
        self.speed_low = Radiobutton(rate_frame, text="Set (Slow)", variable=self.velocity, value='0.1')
        self.speed_low.pack(anchor=W)        
        rate_frame.pack(fill=BOTH, expand=0, side=TOP, padx=5, pady=(0,5))
#--------------------------------------------------------------------------------------------------------#
#========================================================================================================#
        shutter_frame = LabelFrame(left_panel, text=" Telescope Focuser ")
        LT_frame = Frame(shutter_frame, relief=SUNKEN, border=2, background='BLACK')
        LT_frame.pack(fill=BOTH, expand=1, side=TOP, padx=5, pady=(5,0))
        LT_disp = Label(LT_frame, text="--", 
            font = "Arial {font} bold".format(font=UI_FONT_SIZE),
            foreground='RED', background='BLACK')
        LT_disp.pack(fill=BOTH, expand=1)        
        open_button = Button(shutter_frame, text="-", border=1)
        open_button.pack(fill=BOTH, expand=1, side=LEFT, padx=5, pady=5)
        close_button = Button(shutter_frame, text="+", border=1)
        close_button.pack(fill=BOTH, expand=1, side=RIGHT, padx=(0,5), pady=5)        
        shutter_frame.pack(fill=BOTH, expand=0, side=TOP, padx=5, pady=(0,5))        
        # dome controls
        rotate_frame = LabelFrame(left_panel, text=" Dome Functions ")        
        ccw_button = Button(rotate_frame, text=" \nRotate CCW\n ", border=1)
        ccw_button.grid(row=0, column=0, sticky=N+W+E+S, padx=(5,2), pady=(5,2))
        cw_button = Button(rotate_frame, text=" \nRotate CW\n ", border=1)
        cw_button.grid(row=0, column=1, sticky=N+W+E+S, padx=(2,5), pady=(5,2))        
        Separator(rotate_frame, orient=HORIZONTAL).grid(row=1, column=0, columnspan=2, 
            sticky=N+W+E+S, padx=5, pady=2)            
        open_button = Button(rotate_frame, text="Open Slit", border=1)
        open_button.grid(row=2, column=0, sticky=N+W+E+S, padx=(5,2), pady=(2,5))
        close_button = Button(rotate_frame, text="Close Slit", border=1)
        close_button.grid(row=2, column=1, sticky=N+W+E+S, padx=(2,5), pady=(2,5))
        rotate_frame.grid_rowconfigure(0, weight=1)
        rotate_frame.grid_rowconfigure(1, weight=1)
        rotate_frame.grid_columnconfigure(0, weight=1)
        rotate_frame.grid_columnconfigure(1, weight=1)        
        rotate_frame.pack(fill=BOTH, expand=0, side=TOP, padx=5, pady=(0,5))        
        #dome_frame.pack(fill=X, expand=0, padx=5, pady=(5,0), side=TOP)        
        left_panel.pack(fill=BOTH, expand=0, side=LEFT)        
        right_panel = Frame(main_frame)        
        # text output window
        title_bar = Frame(right_panel, relief=RAISED, border=1)        
        time_frame = LabelFrame(title_bar, text="Date/Time Information")        
        time_lt_label = Label(time_frame, text="Local:", font = "Arial {font} bold".format(font=UI_FONT_SIZE))
        time_lt_label.grid(row=0, column=0, padx=(5,0), sticky=N+E+W+S)        
        LT_frame = Frame(time_frame, relief=RAISED, border=2, background='BLACK')
        LT_frame.grid(row=0, column=1, sticky=N+E+W+S)
        self.local_time = Label(LT_frame, text="01/01/2016 - 00:00:00", 
            font = "Arial {font} bold".format(font=UI_FONT_SIZE), background='BLACK',
            foreground='RED')
        self.local_time.pack(fill=BOTH, expand=1)        
        time_ut_label = Label(time_frame, text="UTC:", font = "Arial {font} bold".format(font=UI_FONT_SIZE))
        time_ut_label.grid(row=0, column=2, padx=(5,0), sticky=N+E+W+S)        
        UT_frame = Frame(time_frame, relief=RAISED, border=2, background='BLACK')
        UT_frame.grid(row=0, column=3, sticky=N+E+W+S)
        self.utc_time = Label(UT_frame, text="01/01/2016 - 00:00:00", 
            font = "Arial {font} bold".format(font=UI_FONT_SIZE), background='BLACK',
            foreground='RED')
        self.utc_time.pack(fill=BOTH, expand=1)
        time_lmst_label = Label(time_frame, text="LMST:", font = "Arial {font} bold".format(font=UI_FONT_SIZE))
        time_lmst_label.grid(row=0, column=4, padx=(5,0), sticky=N+E+W+S)        
        LMST_frame = Frame(time_frame, relief=RAISED, border=2, background='BLACK')
        LMST_frame.grid(row=0, column=5, sticky=N+E+W+S, padx=(0,5))
        self.lms_time = Label(LMST_frame, text="00:00:00", 
            font = "Arial {font} bold".format(font=UI_FONT_SIZE), background='BLACK',
            foreground='RED')
        self.lms_time.pack(fill=BOTH, expand=1)        
        time_frame.pack(fill=BOTH, expand=1, padx=5, pady=(0,5), ipadx=5, ipady=2)
        time_frame.grid_columnconfigure(1, weight=1)
        time_frame.grid_columnconfigure(3, weight=1)
        time_frame.grid_columnconfigure(5, weight=1)        
        position_frame = LabelFrame(title_bar, text=" Telescope Guidance ")
        tel_label = Label(position_frame, text="Telescope: ", font = "Arial {font} bold".format(font=UI_FONT_SIZE))
        tel_label.grid(row=1, column=0)        
        header_ra_label = Label(position_frame, text="Right Ascension", font = "Arial {font} bold".format(font=UI_FONT_SIZE))
        header_ra_label.grid(row=0, column=2, sticky=N+E+W+S)        
        RA_frame = Frame(position_frame, relief=RAISED, border=2, background='BLACK')
        RA_frame.grid(row=1, column=2, sticky=N+E+W+S)
        self.RA_disp = Label(RA_frame, text="--",
            font = "Arial {font} bold".format(font=UI_FONT_SIZE), background='BLACK',
            foreground='RED')
        self.RA_disp.pack(fill=BOTH, expand=1)        
        header_dec_label = Label(position_frame, text="Declination", font = "Arial {font} bold".format(font=UI_FONT_SIZE))
        header_dec_label.grid(row=0, column=4, sticky=N+E+W+S)        
        DEC_frame = Frame(position_frame, relief=RAISED, border=2, background='BLACK')
        DEC_frame.grid(row=1, column=4, sticky=N+E+W+S)
        self.DEC_disp = Label(DEC_frame, text="--",
            font = "Arial {font} bold".format(font=UI_FONT_SIZE), background='BLACK',
            foreground='RED')
        self.DEC_disp.pack(fill=BOTH, expand=1)        
        header_ha_label = Label(position_frame, text="Hour Angle", font = "Arial {font} bold".format(font=UI_FONT_SIZE))
        header_ha_label.grid(row=0, column=6,sticky=N+E+W+S)        
        HA_frame = Frame(position_frame, relief=RAISED, border=2, background='BLACK')
        HA_frame.grid(row=1, column=6, sticky=N+E+W+S, padx=(0,5))
        self.HA_disp = Label(HA_frame, text="--",
            font = "Arial {font} bold".format(font=UI_FONT_SIZE), background='BLACK',
            foreground='RED')
        self.HA_disp.pack(fill=BOTH, expand=1)        
        # target
        trg_label = Label(position_frame, text="Target: ", font = "Arial {font} bold".format(font=UI_FONT_SIZE))
        trg_label.grid(row=2, column=0, sticky=E)        
        #tar_ra_label = Label(position_frame, text="RA:", font = "Arial {font} bold".format(font=UI_FONT_SIZE))
        #tar_ra_label.grid(row=1, column=1, sticky=N+E+W+S)        
        trg_RA_frame = Frame(position_frame, relief=RAISED, border=2, background='BLACK')
        trg_RA_frame.grid(row=2, column=2, sticky=N+E+W+S)
        self.trg_RA_disp = Label(trg_RA_frame, text="00h 00m 00s",
            font = "Arial {font} bold".format(font=UI_FONT_SIZE), background='BLACK',
            foreground='ORANGE')
        self.trg_RA_disp.pack(fill=BOTH, expand=1)        
        #trg_header_dec_label = Label(position_frame, text=" DEC:", font = "Arial {font} bold".format(font=UI_FONT_SIZE))
        #trg_header_dec_label.grid(row=1, column=3)        
        trg_DEC_frame = Frame(position_frame, relief=RAISED, border=2, background='BLACK')
        trg_DEC_frame.grid(row=2, column=4, sticky=N+E+W+S)
        self.trg_DEC_disp = Label(trg_DEC_frame, text="+00d 00m 00s",
            font = "Arial {font} bold".format(font=UI_FONT_SIZE), background='BLACK',
            foreground='ORANGE')
        self.trg_DEC_disp.pack(fill=BOTH, expand=1)        
        #trg_header_ha_label = Label(position_frame, text=" HA:", font = "Arial {font} bold".format(font=UI_FONT_SIZE))
        #trg_header_ha_label.grid(row=1, column=5)        
        trg_HA_frame = Frame(position_frame, relief=RAISED, border=2, background='BLACK')
        trg_HA_frame.grid(row=2, column=6, sticky=N+E+W+S, padx=(0,5))
        self.trg_HA_disp = Label(trg_HA_frame, text="+00h 00m 00s",
            font = "Arial {font} bold".format(font=UI_FONT_SIZE), background='BLACK',
            foreground='ORANGE')
        self.trg_HA_disp.pack(fill=BOTH, expand=1)        
        position_frame.pack(fill=BOTH, expand=1, padx=5, pady=(0,5), ipady=2)
        position_frame.grid_columnconfigure(2, weight=1)
        position_frame.grid_columnconfigure(4, weight=1)
        position_frame.grid_columnconfigure(6, weight=1)
        title_bar.pack(fill=BOTH, expand=0, side=TOP)        
        message_window = Frame(right_panel, relief=RAISED, border=1)
        message_frame = LabelFrame(message_window, text="System Messages")        
        # message window
        self.message_window = scrolledtext.ScrolledText(message_frame, 
            relief=SUNKEN,
            border=1,
            background='black',
            foreground='white',
            height = 10)            
        self.message_window.pack(fill=BOTH, expand=1, side=BOTTOM, padx=5, pady=5)
        message_frame.pack(fill=BOTH, expand=1, padx=5, pady=(0,5))
        message_window.pack(fill=BOTH, expand=1)        
        # footer 
        footer_frame = Frame(right_panel, relief=RAISED, border=1)
        auto_frame = LabelFrame(footer_frame, text="Macro Controls")
        auto_frame.pack(fill=X, expand=1, padx=5, pady=(0,5), ipadx=5, ipady=2)                
        footer_frame.pack(fill=X, expand=0)
        right_panel.pack(fill=BOTH, expand=1, side=RIGHT)
        # Created
        photo = PhotoImage(file="stock_media-play.gif")
        self.macro_play = Button(auto_frame, text="Start", image=photo,
                                 relief=FLAT, compound=TOP, border=1,
                                 command=None)
        self.macro_play.image = photo
        self.macro_play.pack(side=LEFT, padx=(2, 0))
        # created
        photo = PhotoImage(file="stock_media-next.gif")
        self.macro_advance = Button(auto_frame, text="Next", image=photo,
                                    relief=FLAT, compound=TOP, border=1,
                                    command=None)
        self.macro_advance.image = photo
        self.macro_advance.pack(side=LEFT, padx=(2, 0))
        main_frame.pack(fill=BOTH, expand=1)        
        self.pack(fill=BOTH, expand=1)        
        self._write_message("NuDomeTracker 0.1 (Python 3 + Tk/Tcl Edition)\n")
        self._write_message("Matthew Cutone, Richard Bloch, and Jesse Rogerson 2009-2016\n")
        self._write_message(LICENSE_TEXT + '\n\n')
        self._write_message("Session data stored in: {}.txt\n".format("sd+20161001"))
        self._write_message("System ready ...\n")
    #def say_hi(self):
    #    self._write_message("NuDomeTracker - Version 0.1:BUILD01142016\n")


    def _on_set_target(self, event=None):
        dlg = TargetDialog.SetTarget(self)


    def connect_argo_navis(self):
        if not self.argo:
            try:
                self.argo = argoterm.ArgoInterface(0)
                self.toggleArgo = 1
            except:
                self._write_message('Error connecting to Argo Navis.\n')
            else:
                self._write_message('Connected to Argo Navis.\n')
        else:
            self.argo = None
            self._write_message('Disconnected from Argo Navis.\n')
            self.toggleArgo = 0

            
    def _on_closing(self, event=None):        
        #self.SystemCore._dec_inter.join()
        #self.SystemCore._ra_inter.join()
        #self.ConnectionsPanel.destroy()
        #self.ConnectionsPanel.CloseAllThreads()
        self.telmover.connect()
        self.telmover.stop_all_ra_motion()
        ra_motioncheck = self.telmover.stop_all_ra_motion()
        print(ra_motioncheck)
        self.telmover.stop_all_dec_motion()
        dec_motioncheck = self.telmover.stop_all_dec_motion()
        print(dec_motioncheck)
        self.telmover.disconnect()
        if ra_motioncheck==1 and dec_motioncheck==1:
            self.SystemCore.CloseAllThreads()
            #self.stopbuttonpress()
            self.master.destroy()
            #quit()

#============================================================================================================#
#--------------------------- ANNA CALIBRATION STUFF - CALIBRATION SETTINGS GUI CALL -------------------------#
#============================================================================================================#      
    def _on_calibration_selection(self, event=None):
        # Call GUI to action
        self.dlg = CalibrationSettings(self.master)
        # Reset Calibration Procedure Controls
       # self.pausethread.config(state="active")
        self.startthread.config(state="active")
        self.killthread.config(state="active")
        self.progressbar["value"] = 0
        # Collect Data from User
        self.yncalib2, self.timecalib2 = self.dlg.multtime()
        self.yncalib1, self.timecalib1 = self.dlg.onetime()
        # Translate the Data into Seconds
        self.IntTime = self.timecalib2[0]
        self.DurTime = self.timecalib2[1]
        self.interval = self.IntTime[0]*60*60                          # repeat interval in seconds
        self.duration = self.DurTime[0]*60*60                          # duration interval in seconds        
        for i in range(1,len(self.IntTime)):
            self.interval = self.interval + self.IntTime[i]*(60*i)
            self.duration = self.duration + self.DurTime[i]*(60*i)
        print(self.duration)
        if self.interval==0:
            # If one-time calibration is selected: start the calibration thread alone
            print('One Time')
            self.showmustgoon=True
            self.spawnthread()
        if self.duration>0 and self.interval>0:
            # If calibration at intervals and then shutdown start another timer
            print('HUI')
            self.DurationCalibration = True
            self.IntervalCalibration = True
            self.durationtimerstarter()
            self.spawnthread()
            return self.interval, self.duration
        if self.interval>0 and self.duration==0:
            # If calibcarion at intervals is selected:
            # 1. Mark that it's a repeated calibration
            self.IntervalCalibration = True
            # 2. Start the calibration thread with timer thread laced in
            self.spawnthread()
            return self.interval
#------------------------------------------------------------------------------------------------------------#
#============================================================================================================#

#============================================================================================================#
#---------------------------- ANNA CALIBRATION STUFF - CALIBRATION THREAD CONTROLS --------------------------#
#============================================================================================================#
# Spawns thread once - releases the kracken
    def spawnthread(self):
        if self.tracking.get()==0:
            self.c.toggle()
            self.c.config(state="disabled")
        if self.tracking.get()==1:
            self.c.config(state="disabled")
        self.tel_north.config(state="disabled")
        self.tel_south.config(state="disabled")
        self.tel_west.config(state="disabled")
        self.tel_east.config(state="disabled")
        self.thread = ThreadedClient(self.queue)
        self.thread.start()
        self.killthread.config(state="normal")
        self.periodiccall()

# Prods the thread with a stick every now and then         
    def periodiccall(self):
        self.showmustgoon, self.endtime = self.thread.stoppedthread()
        if self.showmustgoon==True:            
            self.startthread.config(state="disabled")
            self.checkqueue()            
            if self.thread.is_alive():
                self.after(100, self.periodiccall)
        if self.showmustgoon==False:
            self.stoptheshow()
            self.endtimegetter(self.endtime)
            # In case of repeated calibration start Interval Timer
            if self.IntervalCalibration==True:
                self.startinttimer()

# Checks queue for incoming tasks to do
    def checkqueue(self):
        while self.queue.qsize():
            try:
                msg = self.queue.get(0)
                if msg==2:
                    self.progressbar.step(5.99)
                    time.sleep(0.01)
                    self.progressbar.step(5.99)
                if msg==4:
                    self.progressbar.step(5.99)
                    time.sleep(0.01)
                    self.progressbar.step(5.99)
            except Queue.Empty:
                pass
            
# Starts the show - aka the thread, or continues the thread from last savepoint
    def starttheshow(self):        
        self.showmustgoon = True
        self.pressedstartcount = self.pressedstartcount + 1
        if self.pressedstartcount<=1:
            self.spawnthread()
        else:
            self.periodiccall()

# Stops the calibration by user demand
    def stopbuttonpress(self):
        self.IntervalCalibration = False
        self.stoptheshow()
        
# Resets the settings and re-starts the whole procedure
# This halts the calibration procedure entirely and re-starts it anew
    def stoptheshow(self):
        self.thread.stop()        
        self.c.config(state="normal")
        if self.tracking.get()==1:
            self.c.toggle()
            #self.TrackSky()
        if self.tracking.get()==0:
            print('temp')
            #self.TrackSky()
        self.tel_north.config(state="normal")
        self.tel_south.config(state="normal")
        self.tel_west.config(state="normal")
        self.tel_east.config(state="normal")
        self.startthread.config(state="normal")
        self.killthread.config(state="disabled")
        self.testresult = self.thread.TelTestResult()
        print(self.testresult)
        self.progressbar["value"] = 0
        self.thread.join()
#------------------------------------------------------------------------------------------------------------#
#============================================================================================================#

#============================================================================================================#
#-------------------- ANNA CALIBRATION STUFF - CALIBRATION THREADED INTERVAL TIMER CONTROLS -----------------#
#============================================================================================================#
# Spawns the interval timer thread 
    def startinttimer(self):
        self.inttime = self.interval/100
        self.tinttimer = IntTimer(self.inttime)
        self.tinttimer.start()
        self.pcinttimer()

# Prods the thread with a stick every now and then         
    def pcinttimer(self):
        # Returns whether timer is running or ran out already
        self.intrunning = self.tinttimer.stoppedinttimer()    
        if self.intrunning==True:
            if self.tinttimer.is_alive():
                self.after(100, self.pcinttimer)
        # If the timer ran out re-spawn the calibration thread
        if self.intrunning==False:
            print('Int Timer Ran Out')
            self.spawnthread()            

# Obtained the time when the calibration procedure ends
    def endtimegetter(self, endtime):
        self.endtime = endtime
        return self.endtime

#------------------------------------------------------------------------------------------------------------#
#============================================================================================================#


#============================================================================================================#
#-------------------- ANNA CALIBRATION STUFF - CALIBRATION THREADED DURATION TIMER CONTROLS -----------------#
#============================================================================================================#
# Starts duration timer - makes sur only one can be started
    def durationtimerstarter(self):
        self.durationcounter=0
        if self.DurationCalibration==True:
            self.durationcounter = self.durationcounter + 1
            if self.durationcounter<=1:
                self.startdurtimer()
            else:
                pass

# Spawns the duration timer thread 
    def startdurtimer(self):
        self.durtime = self.duration/100
        print('Start Dur timer')
        self.tdurtimer = DurTimer(self.durtime)
        self.tdurtimer.start()
        self.pcdurtimer()

# Prods the thread with a stick every now and then         
    def pcdurtimer(self):
        # Returns whether timer is running or ran out already
        self.durrunning = self.tdurtimer.stoppeddurtimer()    
        if self.durrunning==True:
            if self.tdurtimer.is_alive():
                self.after(100, self.pcdurtimer)
        # If the timer ran out re-spawn the calibration thread
        if self.durrunning==False:
            self.IntervalCalibration=False
            self.showmustgoon = False
            print('Dur Timer Ran Out')
            self.tdurtimer.join()
        return self.durrunning
#------------------------------------------------------------------------------------------------------------#
#============================================================================================================#

##############################################################################################################
#============================================================================================================#
#===================== ANNA CALIBRATION STUFF - CALIBRATION THREADED INTERVAL TIMER CLASS ===================#
#============================================================================================================#
##############################################################################################################
class IntTimer(threading.Thread):
    def __init__(self, inttime): 
        threading.Thread.__init__(self)
        self.inttime = inttime
        self.intrunning = True

    def run(self):
        try: 
            while True:
                time.sleep(self.inttime)
                self.raise_exception()
        finally: 
            self.intrunning = False
        return self.intrunning 

    def get_id(self):   
        if hasattr(self, '_thread_id'): 
            return self._thread_id 
        for id, thread in threading._active.items(): 
            if thread is self: 
                return id

    def raise_exception(self): 
        thread_id = self.get_id() 
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 
              ctypes.py_object(SystemExit))
        self.intrunning = False
        if res > 1: 
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0) 
            print('Exception raise failure')
        return self.intrunning

# This guy communicates that the timer ran out
    def stoppedinttimer(self):
        return self.intrunning
#------------------------------------------------------------------------------------------------------------#
#============================================================================================================#
 

##############################################################################################################
#============================================================================================================#
#===================== ANNA CALIBRATION STUFF - CALIBRATION THREADED DURATION TIMER CLASS ===================#
#============================================================================================================#
##############################################################################################################
class DurTimer(threading.Thread):
    def __init__(self, durtime): 
        threading.Thread.__init__(self)
        self.durtime = durtime
        self.durrunning = True

    def run(self):
        try: 
            while True:
                time.sleep(self.durtime)
                self.raise_exception()
        finally: 
            self.durrunning = False
        return self.durrunning 

    def get_id(self):   
        if hasattr(self, '_thread_id'): 
            return self._thread_id 
        for id, thread in threading._active.items(): 
            if thread is self: 
                return id

    def raise_exception(self): 
        thread_id = self.get_id() 
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 
              ctypes.py_object(SystemExit))
        self.durrunning = False
        if res > 1: 
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0) 
            print('Exception raise failure')
        return self.durrunning

# This guy communicates that the timer ran out
    def stoppeddurtimer(self):
        return self.durrunning
#------------------------------------------------------------------------------------------------------------#
#============================================================================================================#

##############################################################################################################
#============================================================================================================#
#================================== CALIBRATION PROCEDURE THREADED CLASS ====================================#
#============================================================================================================#
##############################################################################################################
class ThreadedClient(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue        
        self.running = True
        # Connecting to Telescope Controls
        self.telmover = telctrl.TelescopeInterface(('COM5', 'COM6'))
        self.telmover.connect()
        self.telmover.start_tracking()
        # Preparing for Image Taking Calibration
        imageNumberFile = 'CalibrationImages/imageNumberFile.txt'
        # If Image Number File Doesnt Exist Make one
        if not os.path.isfile(imageNumberFile):
            with open(imageNumberFile, 'w') as f:
                f.write('0\n')
        # If Image Number File Exists Write 0 (so that 0 is always the reference image
        if os.path.isfile(imageNumberFile):
            with open(imageNumberFile, 'w') as f:
                f.write('0\n')
        # If Images with these names exist delete them (if caibration will need to repeat)
        calibrationfiles = os.listdir('CalibrationImages/')
        for i in range(len(calibrationfiles)):
            filetype = calibrationfiles[i]
            if filetype.endswith('.fits'):
                img = filetype
                os.remove('CalibrationImages/' + filetype)
            else:
                pass
        # Specify parameters for cooling
        params = {}
        with open('ccdconfig.txt', 'r') as f:
            for line in f.readlines():
                param, value = line.strip().split('=')
                params[param] = int(value)
        self.exposureTime = params['exposureTime']
        self.setpoint = params['setpoint']
        libsbig.open_driver()
        libsbig.open_driver()
        libsbig.open_device()
        libsbig.establish_link()
        libsbig.set_temperature(self.setpoint)
        libsbig.get_ccd_info()        
        self.width_in_pixels = libsbig.get_ccd_info()[0]
        print(self.width_in_pixels)
        self.height_in_pixels = libsbig.get_ccd_info()[1]
        print(self.height_in_pixels)
        Temperature = libsbig.get_temperature()
        CCD_Temp = Temperature[0]
        

# Raises Exception when the Task is Done
    def stop(self):
        thread_id = self.get_id() 
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id,ctypes.py_object(SystemExit))
        self.running=False
        self.telmover.disconnect()
        if res > 1: 
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0) 
            print('Exception raise failure')
        return self.running
        
# The Calibration Procedure 
    def run(self):
        i=0
        try:
            while True:
#00000000000000000000000000000000000000000000000000000000#
                i = i+1
                print(i)
                msg = 'Reference'
                print(msg)
                # Exposing
                libsbig.start_exposure(self.exposureTime, self.width_in_pixels, self.height_in_pixels)
                is_exposing = libsbig.query_command_status()
                while is_exposing == {'Status:': 2}:
                    print("Exposure in Progress")
                    is_exposing = libsbig.query_command_status()
                    time.sleep(0.1)
                    if is_exposing == {'Status:': 3}:
                        print('Exposure Ended')
                        break
                libsbig.end_exposure()
                libsbig.start_readout(self.width_in_pixels, self.height_in_pixels)
                photodata = []
                ii=0
                for ii in range(self.height_in_pixels):  
                    a = libsbig.readout_line(0, self.width_in_pixels, self.width_in_pixels)
                    photodata.append(a)
                libsbig.end_readout()
                libsbig.photoworker(photodata)
                # End Exposing
#1111111111111111111111111111111111111111111111111111111111111#
                i=i+1
                print(i)
                msg = 'Moving North'
                print(msg)
                self.telmover.move_north(0.25)              
                self.queue.put(2)                
                time.sleep(2)
                self.telmover.stop_move('ra')
                self.telmover.stop_move('dec')
                # Exposing
                libsbig.start_exposure(self.exposureTime, self.width_in_pixels, self.height_in_pixels)
                is_exposing = libsbig.query_command_status()
                while is_exposing == {'Status:': 2}:
                    print("Exposure in Progress")
                    is_exposing = libsbig.query_command_status()
                    time.sleep(0.1)
                    if is_exposing == {'Status:': 3}:
                        print('Exposure Ended')
                        break
                libsbig.end_exposure()
                libsbig.start_readout(self.width_in_pixels, self.height_in_pixels)
                photodata = []
                ii=0
                for ii in range(self.height_in_pixels):  
                    a = libsbig.readout_line(0, self.width_in_pixels, self.width_in_pixels)
                    photodata.append(a)
                libsbig.end_readout()
                libsbig.photoworker(photodata)
                # End Exposing
#22222222222222222222222222222222222222222222222222222222222222222222222#
                i=i+1
                print(i)
                msg = 'Moving South'
                print(msg)
                self.telmover.move_south(0.25)
                self.queue.put(4)
                time.sleep(4)
                self.telmover.stop_move('ra')
                self.telmover.stop_move('dec')
                 # Exposing
                libsbig.start_exposure(self.exposureTime, self.width_in_pixels, self.height_in_pixels)
                is_exposing = libsbig.query_command_status()
                while is_exposing == {'Status:': 2}:
                    print("Exposure in Progress")
                    is_exposing = libsbig.query_command_status()
                    time.sleep(0.1)
                    if is_exposing == {'Status:': 3}:
                        print('Exposure Ended')
                        break
                libsbig.end_exposure()
                libsbig.start_readout(self.width_in_pixels, self.height_in_pixels)
                photodata = []
                ii=0
                for ii in range(self.height_in_pixels):  
                    a = libsbig.readout_line(0, self.width_in_pixels, self.width_in_pixels)
                    photodata.append(a)
                libsbig.end_readout()
                libsbig.photoworker(photodata)
                # End Exposing
#3333333333333333333333333333333333333333333333333333333333333333333#
                i=i+1                                
                print(i)
                msg = 'Moving North'
                self.telmover.move_north(0.25)
                self.queue.put(2)
                time.sleep(2)
                self.telmover.stop_move('ra')
                self.telmover.stop_move('dec')
                # Exposing
                libsbig.start_exposure(self.exposureTime, self.width_in_pixels, self.height_in_pixels)
                is_exposing = libsbig.query_command_status()
                while is_exposing == {'Status:': 2}:
                    print("Exposure in Progress")
                    is_exposing = libsbig.query_command_status()
                    time.sleep(0.1)
                    if is_exposing == {'Status:': 3}:
                        print('Exposure Ended')
                        break
                libsbig.end_exposure()
                libsbig.start_readout(self.width_in_pixels, self.height_in_pixels)
                photodata = []
                ii=0
                for ii in range(self.height_in_pixels):  
                    a = libsbig.readout_line(0, self.width_in_pixels, self.width_in_pixels)
                    photodata.append(a)
                libsbig.end_readout()
                libsbig.photoworker(photodata)
                # End Exposing
#444444444444444444444444444444444444444444444444444444444444444444#
                i=i+1
                print(i)
                msg = 'Moving East'
                self.telmover.move_east(0.25)
                self.queue.put(2)
                time.sleep(2)
                self.telmover.stop_move('ra')
                self.telmover.stop_move('dec')
                # Exposing
                libsbig.start_exposure(self.exposureTime, self.width_in_pixels, self.height_in_pixels)
                is_exposing = libsbig.query_command_status()
                while is_exposing == {'Status:': 2}:
                    print("Exposure in Progress")
                    is_exposing = libsbig.query_command_status()
                    time.sleep(0.1)
                    if is_exposing == {'Status:': 3}:
                        print('Exposure Ended')
                        break
                libsbig.end_exposure()
                libsbig.start_readout(self.width_in_pixels, self.height_in_pixels)
                photodata = []
                ii=0
                for ii in range(self.height_in_pixels):  
                    a = libsbig.readout_line(0, self.width_in_pixels, self.width_in_pixels)
                    photodata.append(a)
                libsbig.end_readout()
                libsbig.photoworker(photodata)
                # End Exposing
#55555555555555555555555555555555555555555555555555555555555555555555#
                i=i+1
                print(i)
                msg = 'Moving West'
                self.telmover.move_west(0.25)
                self.queue.put(4)
                time.sleep(4)
                self.telmover.stop_move('ra')
                self.telmover.stop_move('dec')
                # Exposing
                libsbig.start_exposure(self.exposureTime, self.width_in_pixels, self.height_in_pixels)
                is_exposing = libsbig.query_command_status()
                while is_exposing == {'Status:': 2}:
                    print("Exposure in Progress")
                    is_exposing = libsbig.query_command_status()
                    time.sleep(0.1)
                    if is_exposing == {'Status:': 3}:
                        print('Exposure Ended')
                        break
                libsbig.end_exposure()
                libsbig.start_readout(self.width_in_pixels, self.height_in_pixels)
                photodata = []
                ii=0
                for ii in range(self.height_in_pixels):  
                    a = libsbig.readout_line(0, self.width_in_pixels, self.width_in_pixels)
                    photodata.append(a)
                libsbig.end_readout()
                libsbig.photoworker(photodata)
                # End Exposing
#66666666666666666666666666666666666666666666666666666666666666666666#
                i=i+1
                print(i)
                msg = 'Moving East'
                self.telmover.move_east(0.25)
                self.queue.put(2)
                time.sleep(2)
                self.telmover.stop_move('ra')
                self.telmover.stop_move('dec')
                # Exposing
                libsbig.start_exposure(self.exposureTime, self.width_in_pixels, self.height_in_pixels)
                is_exposing = libsbig.query_command_status()
                while is_exposing == {'Status:': 2}:
                    print("Exposure in Progress")
                    is_exposing = libsbig.query_command_status()
                    time.sleep(0.1)
                    if is_exposing == {'Status:': 3}:
                        print('Exposure Ended')
                        break
                libsbig.end_exposure()
                libsbig.start_readout(self.width_in_pixels, self.height_in_pixels)
                photodata = []
                ii=0
                for ii in range(self.height_in_pixels):  
                    a = libsbig.readout_line(0, self.width_in_pixels, self.width_in_pixels)
                    photodata.append(a)
                libsbig.end_readout()
                libsbig.photoworker(photodata)
                # End Exposing
#77777777777777777777777777777777777777777777777777777777777777#
                i=i+1
                print(i)
                msg = 'Analysing'
                self.queue.put(4)
                donutstest.d()                
                self.stop()
        finally:
            i=i+1
            print(i)
            msg = 'Calibration Procedure Ended'
            self.queue.put(4)
            self.running=False
            self.stoppedthread()
        return self.running


# Returns id of the respective thread
    def get_id(self):    
        if hasattr(self, '_thread_id'): 
            return self._thread_id 
        for id, thread in threading._active.items(): 
            if thread is self: 
                return id
          
# Communicates to the MainFrame
    def stoppedthread(self):
        self.endtime = time.time()
        return self.running, self.endtime

    def TelTestResult(self):
        self.testresult = donutstest.d()
        return self.testresult
#------------------------------------------------------------------------------------------------------------#
#============================================================================================================#        
      

##############################################################################################################
#============================================================================================================#
#====================================== CALIBRATION SETTINGS GUI CLASS ======================================#
#============================================================================================================#
##############################################################################################################
class CalibrationSettings:
  def __init__(self, master):
    self.slave = Toplevel(master)
    self.slave.title("Calibration Settings")
    self.slave.geometry("400x250+350+350")
    self.slave.topmost= True
    self.slave.takefocus=True
    self.slave.resizable(width=FALSE, height=FALSE)
    self.slave.focus_set()
    self.initUI()
    self.newValue = 0
    self._on_one_time()

  def initUI(self):
    main_panel = Frame(self.slave)
    main_panel.pack(fill=BOTH, expand=1, side=TOP)
    fraTimeSettings = LabelFrame(main_panel, text="Select Calibration Time")
    fraTimeSettings.pack(fill=X, expand=0, side=TOP, padx=(5,5), pady=(5,5))
    fraTimeSettings.grid_columnconfigure(0, weight=1)
    fraTimeSettings.grid_columnconfigure(1, weight=1)
    fraTimeSettings.grid_columnconfigure(2, weight=1)
    fraInterval = LabelFrame(fraTimeSettings, text="Repeat Interval")
    fraInterval.grid_columnconfigure(1, weight=1)
    fraInterval.grid(row=0, column=0, padx=(5,2), pady=(5,5))
    lblIntHours = Label(fraInterval, text="Hours:")
    lblIntHours.grid(row=0, column=0, padx=(5,5), pady=(5,5), sticky=E)
    self.spnIntHours = Spinbox(fraInterval, from_=0, to=23)
    self.spnIntHours.grid(row=0, column=1, padx=(5,5), pady=(5,5), sticky=E+W) 
    lblIntMin = Label(fraInterval, text="Minutes:")
    lblIntMin.grid(row=1, column=0, padx=(5,5), pady=(0,5), sticky=E)
    self.spnIntMin = Spinbox(fraInterval, from_=0, to=59)
    self.spnIntMin.grid(row=1, column=1, padx=(5,5), pady=(0,5), sticky=E+W)
    lblIntSec = Label(fraInterval, text="Seconds:")
    lblIntSec.grid(row=2, column=0, padx=(5,5), pady=(0,5), sticky=E)
    self.spnIntSec = Spinbox(fraInterval, from_=0, to=59)
    self.spnIntSec.grid(row=2, column=1, padx=(5,5), pady=(0,5), sticky=E+W)        
    fraDuration = LabelFrame(fraTimeSettings, text="Procedure Duration")
    fraDuration.grid_columnconfigure(1, weight=1)
    fraDuration.grid(row=0, column=1, padx=(2,5), pady=(5,5))        
    lblDurHours = Label(fraDuration, text="Hours:")
    lblDurHours.grid(row=0, column=0, padx=(5,5), pady=(5,5), sticky=E)
    self.spnDurHours = Spinbox(fraDuration, from_=0, to=23)
    self.spnDurHours.grid(row=0, column=1, padx=(5,5), pady=(5,5), sticky=E+W)
    lblDurMin = Label(fraDuration, text="Minutes:")
    lblDurMin.grid(row=1, column=0, padx=(5,5), pady=(0,5), sticky=E)
    self.spnDurMin = Spinbox(fraDuration, from_=0, to=59)
    self.spnDurMin.grid(row=1, column=1, padx=(5,5), pady=(0,5), sticky=E+W)
    lblDurSec = Label(fraDuration, text="Seconds:")
    lblDurSec.grid(row=2, column=0, padx=(5,5), pady=(0,5), sticky=E)
    self.spnDurSec = Spinbox(fraDuration, from_=0, to=59)
    self.spnDurSec.grid(row=2, column=1, padx=(5,5), pady=(0,5), sticky=E+W)
    button_box = Frame(self.slave)
    self.close_button = TButton(button_box, text=" Cancel ", command = self.cancelbutton)
    self.close_button.pack(side=RIGHT, padx=(10,0))
    self.okay_button = TButton(button_box, text=" OK ", command = self._on_ok1)
    self.okay_button.pack(side=RIGHT, padx=(10,0))
    self.one_time_button = TButton(button_box, text="One Time Calibration ",command = self.onetime)
    self.one_time_button.pack(side=RIGHT)        
    button_box.pack(fill=X, expand=0, side=BOTTOM, padx=5, pady=5)

# Wait Window method
  def _on_one_time(self):
      self.slave.wait_window()
      CTData = self.CTData
      if self.newValue==1:
          #print(self.newValue)
          #print(self.CTData)
          actiongrabber(self.newValue, self.CTData)
      #return self.newValue

# When user presses cancel button
  def cancelbutton(self):
      self.slave.destroy()
      if event: event.Skip()

# Window Closer
  def _on_close(self, event=None):
      self.slave.destroy()
      if event: event.Skip()

# When user chooses one time calibration
  def onetime(self, event=None):
    self.newValue=1
    self.CTData = [[0,0,0], [0,0,0]]
    self._on_close()
    return self.newValue,  self.CTData

# When user chooses repeated calibration
  def multtime(self, event=None):
      self.newValue=2
      self._on_close()
      return self.newValue,  self.CTData
    
# When user presses Ok Button
  def _on_ok1(self, event=None):
    self.IntHours = int(self.spnIntHours.get())
    self.IntMinutes = int(self.spnIntMin.get())
    self.IntSeconds = int(self.spnIntSec.get())
    self.DurHours = int(self.spnDurHours.get())
    self.DurMinutes = int(self.spnDurMin.get())
    self.DurSeconds = int(self.spnDurSec.get())
    if (self.IntHours==0) and (self.IntMinutes==0) and (self.IntSeconds==0):
          message = 'One Time Calibration Selected \n'
          message = message + 'Do you want to proceed?'
          self.answer = messagebox.askyesno("Information",message, parent=self.slave)
          if self.answer==True:
              self.IntData = [self.IntHours, self.IntMinutes, self.IntSeconds]
              self.DurData = [self.DurHours, self.DurMinutes, self.DurSeconds]
              self.CTData = [self.IntData,self.DurData]
              self.multtime()
          else:
              pass
    if (self.IntHours!=0) or (self.IntMinutes!=0) or (self.IntSeconds!=0):
        self.TotalIntTime = self.IntHours*60*60 + self.IntMinutes*60 + self.IntSeconds
        print(self.TotalIntTime)
        if self.TotalIntTime<=60:
            message = 'Time Interval is Too Short'
            messagebox.showinfo("Error", message)
        else:
            if (self.DurHours==0) and (self.DurMinutes==0) and (self.DurSeconds==0):
                message = 'One Time Calibration Selected \n'
                message = message + 'Do you want to proceed?'
                self.answer = messagebox.askyesno("Information",message, parent=self.slave)
                if self.answer==True:
                    self.IntData = [self.IntHours, self.IntMinutes, self.IntSeconds]
                    self.DurData = [self.DurHours, self.DurMinutes, self.DurSeconds]
                    self.CTData = [self.IntData,self.DurData]
                    self.multtime()
                else:
                    pass
            if (self.DurHours!=0) or (self.DurMinutes!=0) or (self.DurSeconds!=0):
                self.TotalDurTime = self.DurHours*60*60 + self.DurMinutes*60 + self.DurSeconds
                if self.TotalDurTime<=self.TotalIntTime:
                   message = 'One Time Calibration Selected \n'
                   message = message + 'Do you want to proceed?'
                   self.answer = messagebox.askyesno("Information",message, parent=self.slave)
                   if self.answer==True:
                      self.IntData = [self.IntHours, self.IntMinutes, self.IntSeconds]
                      self.DurData = [self.DurHours, self.DurMinutes, self.DurSeconds]
                      self.CTData = [self.IntData,self.DurData]
                      self.multtime()
                   else:
                        pass
                if self.TotalDurTime>=self.TotalIntTime:
                   message = 'Repeated Calibration Selected \n'
                   message = message + 'Do you want to proceed?'
                   self.answer = messagebox.askyesno("Information",message, parent=self.slave)
                   if self.answer==True:
                      self.IntData = [self.IntHours, self.IntMinutes, self.IntSeconds]
                      self.DurData = [self.DurHours, self.DurMinutes, self.DurSeconds]
                      self.CTData = [self.IntData,self.DurData]
                      self.multtime()
                   else:
                      pass
    return self.CTData
    

def CameraChecker(Temperature):
    CCDTEMP = Temperature

# Gets values from Settings
def actiongrabber(newValue, CTData):
    print(newValue)
    print(CTData)
    return(newValue, CTData)
    

def main():
    root = Tk()
    app = MainFrame(root)
    root.mainloop()
    root.quit()    
    return 0


if __name__ == '__main__':
    main()
	
