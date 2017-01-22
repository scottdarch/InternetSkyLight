# InternetSkyLight
A skylight you can install in your internets.

## BeagleBone Green Wifi

Setup instructions for the [BeagleBone Green Wifi](https://beagleboard.org/green-wireless/)
running Debian Jessie.

> We assume you have installed Debian, have a working internet connection,
> and have terminal access to your BeagleBone.

    apt-get install python-imaging
    git clone https://github.com/scottdarch/InternetSkyLight.git
    git clone https://github.com/scanlime/fadecandy.git
    cd fadecandy/server
    make submodules
    make
    ./fcserver &
    cd ../../InternetSkyLight/glue
