#
# Copyright 2017 Scott A Dixon
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
   
#  ___       _                       _     ____  _          _ _       _     _   
# |_ _|_ __ | |_ ___ _ __ _ __   ___| |_  / ___|| | ___   _| (_) __ _| |__ | |_ 
#  | || '_ \| __/ _ \ '__| '_ \ / _ \ __| \___ \| |/ / | | | | |/ _` | '_ \| __|
#  | || | | | ||  __/ |  | | | |  __/ |_   ___) |   <| |_| | | | (_| | | | | |_ 
# |___|_| |_|\__\___|_|  |_| |_|\___|\__| |____/|_|\_\\__, |_|_|\__, |_| |_|\__|
#                                                     |___/     |___/
import math
import numpy as np

class RectangularPixelMatrix(object):
    '''
    Square matrix of pixels.
    '''
    @classmethod
    def on_visit_argparse(cls, parser, subparsers):  # @UnusedVariable
        pixel_args = parser.add_argument_group('Pixel Options')
        #0, 32, 512
        pixel_args.add_argument("--brightness", "-b", type=float, default=1.0, help="Maximum brightness of any given pixel.", metavar="[0.0 - 1.0]")
        pixel_args.add_argument("--channel", default=0, help="OPC channel to use.")
        pixel_args.add_argument("--stride", default=32, help="Number of pixels in a row for the attached matrix")
        pixel_args.add_argument("--pixel-count", default=512, help="Total number of pixels in the attached matrix") 
        
    def __init__(self, args, opc_client):
        super(RectangularPixelMatrix, self).__init__()
        self._opc_client = opc_client
        self._channel = args.channel
        self._pixels = None
        self.stride = args.stride
        self.pixel_count = args.pixel_count
        self.rows = self.stride
        self.brightness = args.brightness
        
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
    
    def fill(self, pixel):
        self.pixels = np.full((self.pixel_count, 3),
                   pixel, 
                   dtype=np.uint8)
        
    def black(self):
        self._pixels = np.zeros((self.pixel_count, 3), dtype=np.uint8)
        self._send()
        
    def blue(self):
        self._pixels = np.full((self.pixel_count, 3), 
                               (0,0,255 * self.brightness), 
                               dtype=np.uint8)
        self._send()
    
    def red(self):
        self._pixels = np.full((self.pixel_count, 3), 
                               (255 * self.brightness,0,0), 
                               dtype=np.uint8)
        self._send()

    def _send(self):
        self._opc_client.put_pixels(self._pixels, channel=self._channel)
