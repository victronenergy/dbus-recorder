# dbus-recorder
Can record and replay data from D-Bus. Used by the Venus OS demo function.

Besides the recorder & replay function, the repo also holds the set of recordings
which is played when enabling the demo function on a Venus device. To run them
yourself, use `play.sh`.

For a full list options, see the help:

```
$ ./dbusrecorder.py --help
Usage: ./dbusrecorder [OPTION]
-h, --help    display this help and exit
-d            set log level to debug (standard info)
-v, --version	returns the program version
--record	    record specified dbus-service to specified file
--duration	  time duration recording in seconds (0 is infinite)
-p            play specified file
--file        filename to record or simulate from
--banner      shows program-name and version at startup
```

## Other utilities

### play.py

This is a more modern rewrite of the play code. It takes multiple arguments,
each of which is file containing a recording. It will replay these recordings
in tandem, keeping events in time sync as recorded.

Note: If you play multiple service recordings of unequal length, the shorter
recording will only restart after the longer one is finished. All events are
played in sync according to their timestamps.

### tools/dump.py

This is a python script that dumps the content of a recording to stdout in csv
format. The content can be viewed, edited and reassembled using `assemble.py`.

The format of the result has the service name in the top-most line, followed
by a block of path/value pairs representing the initial state, followed by an
open line and several lines representing value changes.

The type of a value is represented by prefixing the value with the type, for
example `UINT32:`.

Usage: `python dump.py file.dat > file.csv`

### tools/assemble.py

This is a python script that reassembles a csv created by `dump.py`.

Usage: `python assemble.py file.csv file.dat`
