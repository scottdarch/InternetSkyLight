import math
import numpy as np

class RectangularPixelMatrix(object):
    '''
    Square matrix of pixels.
    '''
    def __init__(self, opc_client, channel, stride, pixel_count):
        super(RectangularPixelMatrix, self).__init__()
        self._opc_client = opc_client
        self._channel = channel
        self._pixels = None
        self.stride = stride
        self.pixel_count = pixel_count
        self.rows = self.stride
        self._brightness = None
        
    @property
    def brightness(self):
        if self._brightness is None:
            return 1.0
        return self._brightness[0][0]
    
    @brightness.setter
    def brightness(self, brightness):
        if brightness < 0 or brightness > 1:
            raise AttributeError("brightness must be a value from 0 to 1")
        self._brightness = np.full((self.pixel_count, 3), 
                               (brightness, brightness, brightness), 
                               dtype=np.float)
        
    @property
    def pixels(self):
        if None is self._pixels:
            self.black()
        return self._pixels
    
    @pixels.setter
    def pixels(self, pixels):
        if None is pixels:
            self.black()
        else:
            self._pixels = pixels
        if self._brightness is not None:
            self._pixels = np.multiply(self._brightness, self._pixels)
        self._send()
        
    def black(self):
        self._pixels = np.zeros((self.pixel_count, 3), dtype=np.uint8)
        self._send()
        
    def blue(self):
        self._pixels = np.full((self.pixel_count, 3), 
                               (0,0,255 * self.brightness), 
                               dtype=np.uint8)
        self._send()
    
    def _send(self):
        self._opc_client.put_pixels(self._pixels, channel=self._channel)
