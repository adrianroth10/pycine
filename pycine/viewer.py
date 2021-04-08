from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg
# backward compatibility default is col-major in pyqtgraph so change
pg.setConfigOptions(imageAxisOrder="row-major")


class Cine_viewer(QtWidgets.QMainWindow):
    def __init__(self, frame_reader):
        super(Cine_viewer, self).__init__()
        self.frame_reader = frame_reader

        self.setWindowTitle("Cine viewer")
        size = (640, 480)
        self.resize(*size)

        layout = QtWidgets.QGridLayout()

        image_view = pg.ImageView()
        self.image_view = image_view
        layout.addWidget(image_view, 0, 0)

        if frame_reader.full_size == 1:
            image = self.frame_reader[0]
            self.image_view.setImage(image)
        else:
            frame_slider = QtWidgets.QSlider()
            frame_slider.setOrientation(QtCore.Qt.Horizontal)
            frame_slider.setMinimum(1) # maybe change to FirstImageNo in cine file
            frame_slider.setMaximum(frame_reader.full_size)
            frame_slider.setTracking(True)  # call update on mouse drag
            frame_slider.setSingleStep(1)
            frame_slider.setValue(frame_reader.start_index + 1)
            self.frame_slider = frame_slider
            layout.addWidget(frame_slider, 1, 0)

            slider_label_left = QtWidgets.QLabel()
            slider_label_left.setText("{}".format(frame_slider.minimum()))
            layout.addWidget(slider_label_left, 2, 0)

            slider_label = QtWidgets.QLabel()
            slider_label.setAlignment(QtCore.Qt.AlignCenter)
            self.slider_label = slider_label
            layout.addWidget(slider_label, 2, 0)

            slider_label_right = QtWidgets.QLabel()
            slider_label_right.setText("{}".format(self.frame_slider.maximum()))
            slider_label_right.setAlignment(QtCore.Qt.AlignRight)
            layout.addWidget(slider_label_right, 2, 0)

            self.update_frame(frame_reader.start_index + 1, autoLevels=True)
            # do this last to avoid double update with slider setValue
            frame_slider.valueChanged.connect(self.update_frame)

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def set_frame(self, frame_index):
        # indirectly call update frame
        self.frame_slider.setValue(frame_index)

    def update_frame(self, frame_index, autoLevels=False):
        image = self.frame_reader[frame_index - 1]
        self.image_view.setImage(image, autoLevels=autoLevels)
        self.slider_label.setText("Frame: {}".format(frame_index))


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
