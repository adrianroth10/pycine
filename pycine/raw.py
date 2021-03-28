import logging
import struct

import numpy as np

from pycine.file import read_header
from pycine.linLUT import linLUT

logger = logging.getLogger()


class Frame_reader:
    def __init__(self, cine_file, header=None, start_index=0, count=None, post_processing=None):
        """
        Create an object for reading frames from a cine file. It can either be used to get specific frames with __getitem__ or as an iterator.

        Parameters
        ----------
        cine_file : str or file-like object
            A string containing a path to a cine file
        header : dict (optional)
            A dictionary contains header information of the cine file
        start_index : int
            First image in a pile of images in cine file. Only used with the iterator in the object.
        count : int
            Maximum number of frames to get if this object is used as an iterator.
        post_processing : function
            Function that takes one image parameter and returns a new processed image
            If provided this function will be applied to the raw image before returning.

        Returns
        -------
        the created object
        """
        self.cine_file = cine_file
        self.cine_file_stream = open(cine_file, "rb")
        self.post_processing = post_processing

        if header is None:
            header = read_header(cine_file)
        self.header = header

        self.start_index = start_index
        self.frame_index = self.start_index

        self.full_size = self.header["cinefileheader"].ImageCount
        if not count:
            count = self.full_size - self.start_index
        self.end_index = self.start_index + count
        if self.end_index > self.full_size:
            raise ValueError("end_index {} is larger than the maximum {}".format(self.end_index, self.full_size))
        self.size = count

    def __getitem__(self, frame_index):
        """
        Dunder method to be able to use [] for retrieving images from the object.

        Parameters
        ----------
        frame_index : int
            the index for the image in cine file to retrieve.
        """
        f = self.cine_file_stream
        f.seek(self.header["pImage"][frame_index])

        annotation_size = struct.unpack("I", f.read(4))[0]
        annotation = struct.unpack("{}B".format(annotation_size - 8), f.read((annotation_size - 8) // 8))
        self.header["Annotation"] = annotation

        image_size = struct.unpack("I", f.read(4))[0]
        data = f.read(image_size)
        image = create_raw_array(data, self.header)
        if not self.post_processing is None:
            image = self.post_processing(image)
        return image

    def __iter__(self):
        return self

    def __next__(self):
        if self.frame_index >= self.end_index:
            raise StopIteration
        logger.debug("Reading frame {}".format(self.frame_index))
        raw_image = self.__getitem__(self.frame_index)
        self.frame_index += 1
        return raw_image

    def __len__(self):
        return self.size

    def __del__(self):
        self.cine_file_stream.close()


def frame_reader(cine_file, header=None, start_frame=1, count=None):
    return Frame_reader(cine_file, header, start_frame - 1, count)


def read_bpp(header):
    """
    Get bit depth (bit per pixel) from header

    Parameters
    ----------
    header : dict
        A dictionary contains header information of the cine file

    Returns
    -------
    bpp : int
        Bit depth of the cine file
    """
    if header["bitmapinfoheader"].biCompression:
        bpp = 12
    else:
        bpp = header["setup"].RealBPP
    return bpp


def image_generator(cine_file, start_frame=False, start_frame_cine=False, count=None):
    """
    Get only a generator of raw images for specified cine file.

    Parameters
    ----------
    cine_file : str or file-like object
        A string containing a path to a cine file
    start_frame : int
        First image in a pile of images in cine file.
        If 0 is given, it means the first frame of the saved images would be readed in this function.
        Only start_frame or start_frame_cine should be specified.
        If both are specified, raise ValueError.
    start_frame_cine : int
        First image in a pile of images in cine file.
        This number corresponds to the frame number in Phantom Camera Control (PCC) application.
        Only start_frame or start_frame_cine should be specified.
        If both are specified, raise ValueError.
    count : int
        maximum number of frames to get.

    Returns
    -------
    raw_image_generator : generator
        A generator for raw image
    """
    header = read_header(cine_file)
    if type(start_frame) == int and type(start_frame_cine) == int:
        raise ValueError("Do not specify both of start_frame and start_frame_cine")
    elif start_frame == False and start_frame_cine == False:
        fetch_head = 1
    elif type(start_frame) == int:
        fetch_head = start_frame
    elif type(start_frame_cine) == int:
        numfirst = header["cinefileheader"].FirstImageNo
        numlast = numfirst + header["cinefileheader"].ImageCount - 1
        fetch_head = start_frame_cine - numfirst
        if fetch_head < 0:
            strerr = "Cannot read frame %d. This cine has only from %d to %d."
            raise ValueError(strerr % (start_frame_cine, numfirst, numlast))
    raw_image_generator = frame_reader(cine_file, header, start_frame=fetch_head, count=count)
    return raw_image_generator


def read_frames(cine_file, start_frame=False, start_frame_cine=False, count=None):
    """
    Get a generator of raw images for specified cine file.

    Parameters
    ----------
    cine_file : str or file-like object
        A string containing a path to a cine file
    start_frame : int
        First image in a pile of images in cine file.
        If 0 is given, it means the first frame of the saved images would be readed in this function.
        Only start_frame or start_frame_cine should be specified.
        If both are specified, raise ValueError.
    start_frame_cine : int
        First image in a pile of images in cine file.
        This number corresponds to the frame number in Phantom Camera Control (PCC) application.
        Only start_frame or start_frame_cine should be specified.
        If both are specified, raise ValueError.
    count : int
        maximum number of frames to get.

    Returns
    -------
    raw_image_generator : generator
        A generator for raw image
    setup : pycine.cine.tagSETUP class
        A class containes setup data of the cine file
    bpp : int
        Bit depth of the raw images
    """
    header = read_header(cine_file)
    bpp = read_bpp(header)
    setup = header["setup"]
    raw_image_generator = image_generator(cine_file, start_frame, start_frame_cine, count)
    return raw_image_generator, setup, bpp


def unpack_10bit(data, width, height):
    packed = np.frombuffer(data, dtype="uint8").astype(np.uint16)
    unpacked = np.zeros([height, width], dtype="uint16")

    unpacked.flat[::4] = (packed[::5] << 2) | (packed[1::5] >> 6)
    unpacked.flat[1::4] = ((packed[1::5] & 0b00111111) << 4) | (packed[2::5] >> 4)
    unpacked.flat[2::4] = ((packed[2::5] & 0b00001111) << 6) | (packed[3::5] >> 2)
    unpacked.flat[3::4] = ((packed[3::5] & 0b00000011) << 8) | packed[4::5]

    return unpacked


def unpack_12bit(data, width, height):
    packed = np.frombuffer(data, dtype="uint8").astype(np.uint16)
    unpacked = np.zeros([height, width], dtype="uint16")
    unpacked.flat[::2] = (packed[::3] << 4) | packed[1::3] >> 4
    unpacked.flat[1::2] = ((packed[1::3] & 0b00001111) << 8) | (packed[2::3])

    return unpacked


def create_raw_array(data, header):
    width, height = header["bitmapinfoheader"].biWidth, header["bitmapinfoheader"].biHeight

    if header["bitmapinfoheader"].biCompression == 0:  # uncompressed data
        if header["bitmapinfoheader"].biBitCount == 16:  # 16bit
            raw_image = np.frombuffer(data, dtype="uint16")
        if header["bitmapinfoheader"].biBitCount == 8:  # 8bit
            raw_image = np.frombuffer(data, dtype="uint8")
        raw_image.shape = (height, width)
        raw_image = np.flipud(raw_image)
        raw_image = np.interp(
            raw_image, [header["setup"].BlackLevel, header["setup"].WhiteLevel], [0, 2 ** header["setup"].RealBPP - 1]
        ).astype(np.uint16)

    elif header["bitmapinfoheader"].biCompression == 256:  # 10bit / P10 compressed
        raw_image = unpack_10bit(data, width, height)
        raw_image = linLUT[raw_image].astype(np.uint16)
        # fixes black and white levels as mentioned in the file documentation, however the values 64 and 1014 do no represent the tested images properly
        raw_image = np.interp(raw_image, [64, 4064], [0, 2 ** 12 - 1]).astype(np.uint16)

    elif header["bitmapinfoheader"].biCompression == 1024:  # 12bit / P12L compressed
        raw_image = unpack_12bit(data, width, height)
        raw_image = np.interp(
            raw_image, [header["setup"].BlackLevel, header["setup"].WhiteLevel], [0, 2 ** header["setup"].RealBPP - 1]
        ).astype(np.uint16)

    return raw_image
