[pyramid_geoip][] integrates the [MaxMind][] GeoIP database with a [Pyramid][]
/ SQLAlchemy web application. You can use it to locate incoming requests by
their IP address:

    data = request.geoip('89.16.224.130')

    data['city'], data['country_code']
    -> 'London', 'GB'
    
    data['latitude'], data['longitude']
    -> 51.514199999999988, -0.093099999999992633

Note that [pyramid_geoip][] stores GeoIP data in an *SQL database* (as opposed
to storing it on the filesystem) and reads all the data (many MB) into *memory*
on application start. This may well *not* be the pattern / setup you want, in
which case you may find it better to integrate yourself using [pygeoip][].

## Install

Install using [pip][]:

    pip install pyramid_geoip

Create a `blobs` database table, corresponding to the
[pyramid_basemodel.blob.Blob][] model class, e.g.: using [alembic][]:

    alembic -c $PASTE_CONFIG revision --autogenerate
    alembic -c $PASTE_CONFIG upgrade head

## Configure

[Configure your application][] to include the package (n.b.: see the notes in
the update section below before you deploy):

    config.include('pyramid_geoip')

Optionally override the data sources, using your
[PasteDeploy configuration file][]:

    geoip.cities_ip4_url=https://example.com/GeoLiteCity.dat.gz
    geoip.cities_ip6_url=https://example.com/GeoLiteCityv6.dat.gz

You can also use locally vendored data files, which will override the urls / 
read from db machinery if present. The defaults looked for are:

    geoip.cities_ip4_path=vendor/GeoLiteCity.dat
    geoip.cities_ip6_path=vendor/GeoLiteCityv6.dat

## Use

Use the utility provided at `request.geoip` to lookup data by IP address, e.g.
in a [view callable][]: 
    
    data = request.geoip()

By default, this will use the ip address for the incoming request (read from
the `REMOTE_ADDR` in the [WSGI environment][], or from the value of the
`X-Forwarded-For` header if provided by a [load balancer or proxy][]). Note
also that it will work for IPv4 and IPv6 addresses.

To specify the address yourself, e.g.:

    data = request.geoip('89.16.224.130')
    
The data contains country, region, city, lat lng, etc.:

    data['country_code']  # 'GB'
    data['city']          # 'London'
    data['latitude']      # 51.514199999999988
    data['longitude']     # -0.093099999999992633

## Update

MaxMind data loses accuracy over time and consequently MaxMind ship new data
every month -- specifically on the first Tuesday of each month. You can call
the update module as a script to fetch the latest data:

    python ./pyramid_geoip/update.py

Note that you may want to:

1. run this script before you `config.include` the package in your main
   application configuration (as it takes time to download the data and your
   application will hang starting up until the data is available)
1. schedule this to run monthly

## Tests

To run the tests, `pip install nose coverage mock` and e.g.:

    $ nosetests pyramid_geoip --with-doctest --with-coverage --cover-tests --cover-package pyramid_geoip
    ......
    Name                       Stmts   Miss  Cover   Missing
    --------------------------------------------------------
    pyramid_geoip                 10      0   100%   
    pyramid_geoip.interfaces       4      0   100%   
    pyramid_geoip.lookup          69      0   100%   
    pyramid_geoip.update          12      0   100%   
    --------------------------------------------------------
    TOTAL                         95      0   100%   
    ----------------------------------------------------------------------
    Ran 6 tests in 0.041s
    
    OK


[pyramid_geoip]: https://github.com/thruflo/pyramid_geoip
[MaxMind]: http://www.maxmind.com/en/home
[Pyramid]: http://pyramid.readthedocs.org
[pygeoip]: https://pypi.python.org/pypi/pygeoip
[pip]: http://www.pip-installer.org
[pyramid_basemodel.blob.Blob]: https://github.com/thruflo/pyramid_basemodel/blob/master/src/pyramid_basemodel/blob.py
[alembic]: http://alembic.readthedocs.org/en/latest/tutorial.html#auto-generating-migrations
[Configure your application]: http://pyramid.readthedocs.org/en/latest/narr/configuration.html
[view callable]: http://pyramid.readthedocs.org/en/latest/narr/views.html
[PasteDeploy configuration file]: http://pyramid.readthedocs.org/en/latest/narr/paste.html
[WSGI environment]: http://en.wikipedia.org/wiki/Web_Server_Gateway_Interface
[load balancer or proxy]: http://en.wikipedia.org/wiki/X-Forwarded-For
