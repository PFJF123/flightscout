# vhs tape for the flightscout README demo GIF.
# Run from the repo root:  vhs demo.tape   (produces demo.gif)
Output demo.gif

Set FontSize 15
Set Width 1180
Set Height 760
Set Padding 16
Set Theme "Dracula"
Set TypingSpeed 45ms

Hide
Type "export FLIGHTSCOUT_HOME=/tmp/fs-gif; rm -rf /tmp/fs-gif; export PATH=$PWD/.venv/bin:$PATH; clear"
Enter
Show

Sleep 700ms
Type "flightscout search BOS BCN 2026-09-15 --limit 3"
Sleep 500ms
Enter
Sleep 5s

Type "flightscout cheapest BOS BCN --from 2026-09-10 --to 2026-09-18"
Sleep 500ms
Enter
Sleep 5s

Type "# compare nearby airports"
Enter
Type "flightscout compare BOS,PVD BCN 2026-09-15 --limit 3"
Sleep 500ms
Enter
Sleep 5s

Type "# set a watch: alert me the day this opens for booking"
Enter
Type 'flightscout watch add availability BOS BCN 2027-05-09 --label "Barcelona trip"'
Sleep 500ms
Enter
Sleep 2s

Type "flightscout watch list"
Sleep 500ms
Enter
Sleep 4s
