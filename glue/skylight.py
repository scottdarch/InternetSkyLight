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

# pip install pyephem
import ephem
# pip install requests
import requests

import opc


# pip install Pillow
try:
    import Image
    from Image import BICUBIC
    import ImageEnhance
except ImportError:
    from PIL import Image
    from PIL.Image import BICUBIC
    from PIL import ImageEnhance

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
    def __init__(self, url, source_box, brightness, cityname):
        super(WebCam, self).__init__()
        self.url = url
        self._source_box = source_box
        self._brightness = brightness
        self._observer = None
        if cityname is not None:
            try:
                self._observer = ephem.city(cityname)
            except KeyError as e:
                # If you city is not found you can build an observer yourself.
                # See http://rhodesmill.org/pyephem/quick.html for details
                print str(e)
            except Exception as e:
                print str(e)
                print "pyephem is not working correctly."
        
    def sample(self, display_width_pixels, display_height_pixels, show=False):
        sampled_image = self._sample_webcam_image(display_width_pixels, display_height_pixels)
        enchancer = ImageEnhance.Brightness(sampled_image)
        if self._is_sun_down():
            sampled_image = enchancer.enhance(0)
            print "sun is down. Returning black."
        elif self._brightness != 1:
            sampled_image = enchancer.enhance(self._brightness)
            
        if show:
            sampled_image.show()
        return self._sampled_pixels_to_flat(display_width_pixels, display_height_pixels, sampled_image.load())
    
    # +------------------------------------------------------------------------+
    # | PRIVATE
    # +------------------------------------------------------------------------+

    def _sampled_pixels_to_flat(self, display_width_pixels, display_height_pixels, sampled_pixel_access):
        flat_pixels = []
        for y in xrange(0, display_height_pixels):
            for x in xrange(0, display_width_pixels):
                flat_pixels.append(sampled_pixel_access[x,y])
        return flat_pixels
        
    def _sample_webcam_image(self, display_width_pixels, display_height_pixels):
        webcam_request = requests.get(self.url)
        webcam_source_image = Image.open(StringIO(webcam_request.content))
        source_region = webcam_source_image.crop(self._source_box)
        return source_region.resize((display_width_pixels, display_height_pixels), resample=BICUBIC)

    def _is_sun_down(self):
        if self._observer is None:
            return False
        sun = ephem.Sun()
        now = ephem.now()
        next_rising = self._observer.next_rising(sun)
        next_setting = self._observer.next_setting(sun)
        if now < next_rising and next_setting > next_rising:
            # now is before the sunrise and the next sunset is after
            # the sunrise then the sun is down.
            return True
        else:
            return False
        
            
# +---------------------------------------------------------------------------+
# | MAIN
# +---------------------------------------------------------------------------+

_opc_fps = 10
_opc_update_minutes = 1

def main():
    parser = argparse.ArgumentParser(
            prog=__app_name__, description="Open Pixel Controller client to simulate a skylight.")
    parser.add_argument('-c', '--cam', help="URL to a webcam image", required=True)
    parser.add_argument('-p', '--port', help="TCP port to connect to OPC server on.", default=7890, type=int)
    parser.add_argument('--brightness', help="Brightness value to apply to the webcam image", default=1.0, type=float)
    parser.add_argument('-b', '--box', help="4 values; left-x, top-y, width-pixels, height-pixels specifying a sub-region of webcam image to sample.", nargs="+", type=int)
    parser.add_argument('-s', '--show', help="Use python imaging (or Pillow) to show the pixel source locally.", action="store_true")
    parser.add_argument('--city', help="If an observer city is found the skylight image is always black after sundown until sunrise.")
    
    args = parser.parse_args()
    
    print str(args.box)
    opc_client = opc.Client("127.0.0.1:{}".format(args.port))
    
    while(not opc_client.can_connect()):
        print 'Waiting for {}...'.format(opc_client._port)
        time.sleep(1)
     
    print 'connected to {}'.format(opc_client._port)
    
    panel0 = SquarePixelMatrix(opc_client, 0, 64)
    cam = WebCam(args.cam, args.box, args.brightness, args.city)
    
    pixels = None
    
    try:
        last_update = _opc_update_minutes * (60 * _opc_fps)

        while(1):
            last_update += 1
            if last_update >= (_opc_update_minutes * (60 * _opc_fps)):
                last_update = 0
                pixels = cam.sample(panel0.stride, panel0.rows, args.show)
                print "Updating from {}".format(cam.url)
            panel0.set_pixels(pixels)
            time.sleep(1.0 / float(_opc_fps))
    except KeyboardInterrupt:
        panel0.black()
    
    opc_client.disconnect()

if __name__ == "__main__":
    main()
