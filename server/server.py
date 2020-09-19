import io
import os
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import syslog
import time
from PIL import Image
import zmq

IS_PRODUCTION = os.uname()[4][:3] == "arm"


class MockMatrix:
    def SetImage(self, im):
        byte_io = io.BytesIO()
        im.save(byte_io, format="PPM")
        print("[{}] {}".format(time.time(), byte_io.getbuffer().nbytes))


def matrix_factory(width):
    options = RGBMatrixOptions()
    options.rows = width
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = "adafruit-hat"
    panel = RGBMatrix(options=options)
    return panel


class Panel:
    def __init__(self):
        self.prev_byte_io = None
        self.panel = matrix_factory(32) if IS_PRODUCTION else MockMatrix()

    def draw(self, message):
        byte_io = io.BytesIO(message)

        if not compare_bytes(self.prev_byte_io, byte_io):
            self.prev_byte_io = byte_io
            im = Image.open(byte_io)
            self.panel.SetImage(im.convert("RGB"))


def get_bytes(byte_io):
    return list(bytes(byte_io.getvalue()))


def is_byte_io(val):
    return isinstance(val, io.BytesIO)


def compare_bytes(a, b):
    return is_byte_io(a) and is_byte_io(b) and get_bytes(a) == get_bytes(b)


panel = Panel()
context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

while True:
    try:
        message = socket.recv()
        panel.draw(message)
        socket.send(b"1")
    except Exception as e:
        syslog.syslog(syslog.LOG_ERR, str(e))
        print(e)
        try:
            socket.send(b"0")
        except:
            pass
