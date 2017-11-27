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
-c            enable tracing to console (standard off)
-t            enable tracing to file (standard off)
-d            set tracing level to debug (standard info)
-v, --version	returns the program version
--record	    record specified dbus-service to specified file
--duration	  time duration recording in seconds (0 is infinite)
-p            play specified file
--file        filename to record or simulate from
--banner      shows program-name and version at startup
```
