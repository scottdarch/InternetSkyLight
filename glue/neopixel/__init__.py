import math


class SquarePixelMatrix(object):
    '''
    Square matrix of pixels.
    '''
    def __init__(self, opc_client, channel, pixel_count):
        super(SquarePixelMatrix, self).__init__()
        self._opc_client = opc_client
        self._channel = channel
        self._pixels = None
        self.pixel_count = pixel_count
        self.stride = int(math.sqrt(pixel_count))
        self.rows = self.stride
    
    def get_pixels(self):
        if None is self._pixels:
            self.black()
        return self._pixels
    
    def set_pixels(self, pixels):
        if None is pixels:
            self.black()
        else:
            self._pixels = pixels
        self._send()
        
    def black(self):
        self._pixels = [(0,0,0)] * self.pixel_count
        self._send()
        
    def blue(self):
        self._pixels = [(0,0,255)] * self.pixel_count
        self._send()
    
    def _send(self):
        self._opc_client.put_pixels(self._pixels, channel=self._channel)
