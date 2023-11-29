import sys
from PySide6.QtWidgets import QMainWindow, QApplication, QLabel, QVBoxLayout, QWidget, QStackedLayout
from PySide6.QtCore import Qt, QTimer

# the countdown time in seconds
# COUNTDOWN_SEC = 300
COUNTDOWN_SEC = 300 

# convert the timer from sec to min:sec
def secs_to_minsec(secs:int):
    mins = secs // 60
    secs = secs % 60
    minsec = f'{mins:02}:{secs:02}'
    return minsec

# add widget to the GUI
def addLayoutWidget(label, font_size, font_type):
    widget = QLabel(label)
    widget.setStyleSheet("font: {}pt {}".format(font_size,font_type))
    widget.setAlignment(Qt.AlignHCenter)

    return widget

# display the new GUI after the CD timer reaches zero
def AutomationLayout(self):
    layout_z = QStackedLayout()
    text_str = "Automation in Progress\n Please do not turn off the Windows and FPGA!"
    widget_z = QLabel(text_str)
    widget_z.setStyleSheet("font: 25pt Arial Black")
    widget_z.setAlignment( Qt.AlignmentFlag.AlignHCenter| Qt.AlignmentFlag.AlignVCenter)

    layout_z.addWidget(widget_z)

    new_widget = QWidget()
    new_widget.setLayout(layout_z)
    self.setCentralWidget(new_widget)
    self.showMaximized()

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.w = None
        # the COUNTDOWN TIMER
        self.time_left_int = COUNTDOWN_SEC
        self.myTimer = QTimer(self)

        self.setWindowTitle("Automation")

        layout = QVBoxLayout()

        # the text that appear on the screen
        str1 = "AUTOMATION IS RUNNING"
        str2 = "Please exit your tasks in :"

        # the empty widget that occupies the top part of the screen for better representation
        empty_widget1 = addLayoutWidget('', 25, '')
        widget1 = addLayoutWidget(str1, 50, "Cambria")  # display the text widget
        widget2 = addLayoutWidget(str2, 25, "Times New Roman") # display the text widget
        empty_widget = addLayoutWidget('', 25, '') # display the empty widget at the bottom section

        # the timer widget that responsible for the cd timer display
        cd_widget = QLabel(secs_to_minsec(COUNTDOWN_SEC))
        cd_widget.setStyleSheet("font: 100pt Helvetica")
        cd_widget.setAlignment(Qt.AlignHCenter)
        self.timerLabel = cd_widget

        layout.addWidget(empty_widget1)
        layout.addWidget(widget1)
        layout.addWidget(widget2)
        layout.addWidget(self.timerLabel)
        layout.addWidget(empty_widget)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.showMaximized()

        self.start_Timer()
        self.update_gui()

        if self.time_left_int == 0:
            AutomationLayout()

    def start_Timer(self):
        self.time_left_int = COUNTDOWN_SEC
        self.myTimer.timeout.connect(self.timerTimeout)
        self.myTimer.start(1000)

    def timerTimeout(self):
        if self.time_left_int != 0:
            self.time_left_int -= 1
            self.update_gui()
        else:
            # AutomationLayout(self)
            self.myTimer.stop()
            AutomationLayout(self)

    def update_gui(self):
        minsec = secs_to_minsec(self.time_left_int)
        self.timerLabel.setText(minsec)

app = QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec())
