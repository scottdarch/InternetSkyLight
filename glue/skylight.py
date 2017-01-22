#!/usr/bin/env python2

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


from StringIO import StringIO
import argparse
import math
import time

# pip install Pillow
try:
    import Image
    from Image import BICUBIC
except ImportError:
    from PIL import Image
    from PIL.Image import BICUBIC
    
import requests

import opc


__app_name__ = "skylight"

# +---------------------------------------------------------------------------+
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
    
    def set_pixels(self, pixels):
        if None is pixels:
            self.black()
        else:
            self._pixels = pixels
        self._send()
        
    def black(self):
        self._pixels = [(0,0,0)] * self.pixel_count
        self._send()
    
    def _send(self):
        self._opc_client.put_pixels(self._pixels, channel=self._channel)

# +---------------------------------------------------------------------------+
class WebCam(object):
    '''
    Access to a webcam image and mechanisms to extract resampled pixel arrays.
    '''
    def __init__(self, url, source_box, gamma):
        super(WebCam, self).__init__()
        self.url = url
        self._source_box = source_box
        self._gamma = gamma
        
    def sample(self, out_width_pixels, out_height_pixels):
        sampled = self._sample_webcam_image(out_width_pixels, out_height_pixels)
        return self._sampled_pixels_to_flat_with_adjustments(out_width_pixels, out_height_pixels, sampled.load())
        
    
    def show_sample(self, out_width_pixels, out_height_pixels):
        sampled = self._sample_webcam_image(out_width_pixels, out_height_pixels)
        sampled.show()
    
    def _sampled_pixels_to_flat_with_adjustments(self, out_width_pixels, out_height_pixels, sampled_pixel_access):
        flat_pixels = []
        for y in xrange(0, out_height_pixels):
            for x in xrange(0, out_width_pixels):
                flat_pixels.append(self._gamma_correct_24bit_rgb(sampled_pixel_access[x,y]))
        return flat_pixels
        
    def _sample_webcam_image(self, out_width_pixels, out_height_pixels):
        webcam_request = requests.get(self.url)
        webcam_source_image = Image.open(StringIO(webcam_request.content))
        source_region = webcam_source_image.crop(self._source_box)
        return source_region.resize((out_width_pixels, out_height_pixels), resample=BICUBIC)
    
    def _gamma_correct_24bit_rgb(self, rgb_value):
        return (self._gamma_correct_8bit_value(rgb_value[0]),
                self._gamma_correct_8bit_value(rgb_value[1]),
                self._gamma_correct_8bit_value(rgb_value[2]))
    
    def _gamma_correct_8bit_value(self, value):
        return int(((float(value) / 255.0) ** self._gamma) * 255.0)
        
# +---------------------------------------------------------------------------+
# | MAIN
# +---------------------------------------------------------------------------+

_opc_fps = 10
_opc_update_minutes = 1

def main():
    parser = argparse.ArgumentParser(
            prog=__app_name__, description="Open Pixel Controller client to simulate a skylight.")
    parser.add_argument('-p', '--port', default=7890, type=int)
    parser.add_argument('-c', '--cam', help="URL to a webcam image", default="http://wwc.instacam.com/instacamimg/SALTY/SALTY_l.jpg")
    parser.add_argument('-g', '--gamma', help="Gamma value to apply to the webcam image", default=1.0, type=float)
    
    args = parser.parse_args()
    
    opc_client = opc.Client("127.0.0.1:{}".format(args.port))
    
    while(not opc_client.can_connect()):
        print 'Waiting for {}...'.format(opc_client._port)
        time.sleep(1)
     
    print 'connected to {}'.format(opc_client._port)
    
    panel0 = SquarePixelMatrix(opc_client, 0, 64)
    cam = WebCam(args.cam, (0, 0, 400, 400), args.gamma)
    
    pixels = None
    
    try:
        last_update = _opc_update_minutes * (60 * _opc_fps)

        while(1):
            last_update += 1
            if last_update >= (_opc_update_minutes * (60 * _opc_fps)):
                last_update = 0
                pixels = cam.sample(panel0.stride, panel0.rows)
                print "Updating from {}".format(cam.url)
            panel0.set_pixels(pixels)
            time.sleep(1.0 / float(_opc_fps))
    except KeyboardInterrupt:
        panel0.black()
    
    opc_client.disconnect()

if __name__ == "__main__":
    main()
