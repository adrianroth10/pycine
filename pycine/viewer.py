from PyQt5 import QtCore, QtWidgets  # , QtGui
import pyqtgraph as pg

# import numpy as np


class Cine_viewer(QtWidgets.QMainWindow):
    def __init__(self, frame_reader, *args, **kwargs):
        super(Cine_viewer, self).__init__(*args, **kwargs)
        self.frame_reader = frame_reader

        self.setWindowTitle("Cine viewer")
        size = (640, 480)
        self.resize(*size)

        layout = QtWidgets.QGridLayout()

        image_view = pg.ImageView()
        self.image_view = image_view
        layout.addWidget(image_view, 0, 0)

        frame_slider = QtWidgets.QSlider()
        frame_slider.setOrientation(QtCore.Qt.Horizontal)
        frame_slider.setMinimum(0)
        frame_slider.setMaximum(frame_reader.full_size - 1)
        frame_slider.setTracking(True)
        frame_slider.setSingleStep(1)
        frame_slider.valueChanged.connect(self.update_frame)
        self.frame_slider = frame_slider
        layout.addWidget(frame_slider, 1, 0)

        slider_label = QtWidgets.QLabel()
        slider_label.setAlignment(QtCore.Qt.AlignCenter)
        self.slider_label = slider_label
        layout.addWidget(slider_label, 2, 0)

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        if frame_reader.start_index == 0:
            # since this is the same as default slider val a manual call to update slider is required
            self.update_frame()
        else:
            self.set_frame(frame_reader.start_index)

    def set_frame(self, frame_index):
        # indirectly call update frame
        self.frame_slider.setValue(frame_index)

    def update_frame(self):
        frame_index = self.frame_slider.value()
        image = self.frame_reader[frame_index]
        self.image_view.setImage(image)
        self.slider_label.setText("Frame: {}".format(frame_index + 1))


def view_cine(frame_reader):
    """Start an interactive viewer for a cine file

    Parameters
    ----------
    frame_reader : pycine.raw.Frame_reader
        Object for the cine_file to be viewed

    Returns
    -------
    None
    """
    app = QtWidgets.QApplication([])
    window = Cine_viewer(frame_reader)
    window.show()

    # Start the event loop.
    app.exec_()
