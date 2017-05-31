# InternetSkyLight
A skylight you can install in your internets.

TODO
* use pyephem to simulate moonlight
* add some sample webcam URLs from around the world.
* support more pixel topologies

## Hardware

* BeagleBone Green Wifi
* AdaFruit fadecandy
* RGB or RGBW LED arrays or strips
* A big power supply for your LEDs

## BeagleBone Green Wifi

Setup instructions for the [BeagleBone Green Wifi](https://beagleboard.org/green-wireless/)
running Debian Jessie.

> We assume you have installed Debian, have a working internet connection,
> and have terminal access to your BeagleBone.

    apt-get install python-imaging
    pip install pyephem
    git clone https://github.com/scottdarch/InternetSkyLight.git
    git clone https://github.com/scanlime/fadecandy.git
    cd fadecandy/server
    make submodules
    make
    ./fcserver &
    cd ../../InternetSkyLight/glue

> Note you may need to `pip install requests` but the latest versions of
> Debian appear to have this pre-installed.

### Install Services

    cp ~/fadecandy/server/fcserver /usr/bin

#### /lib/systemd/system/fcserver.service

    [Unit]
    Description=fadecandy server (runs on port 7890)
    After=network.target

    [Service]
    Type=simple
    ExecStart=/usr/bin/fcserver

    [Install]
    WantedBy=multi-user.target

 then

    systemctl enable fcserver.service

#### /lib/systemd/system/skylight-seattle.service

Run a skylight using a Seattle Washington USA webcamera

    [Unit]
    Description=Seattle WA skylight
    After=fcserver.service

    [Service]
    Type=simple
    ExecStart=/root/InternetSkyLight/glue/skylight.py -c http://wwc.instacam.com/instacamimg/SALTY/SALTY_l.jpg --box 0 0 1028 350 --city Seattle

    [Install]
    WantedBy=multi-user.target

then

    systemctl enable skylight-seattle.service

## Some Example Cams

**Seattle Skyline**

    skylight.py -c http://wwc.instacam.com/instacamimg/SALTY/SALTY_l.jpg --box 0 0 1028 350 --city Seattle

**Mount Arunachala, Tiruvannamalai, India**

    skylight.py -c http://www.arunachala-live.com/live/video.jpg --box 0 0 800 200
