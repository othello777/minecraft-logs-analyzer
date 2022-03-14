# Minecraft-Logs-Analyzer
A tool to analyze game logs generated by Minecraft. This is done to calculate the total playtime based on the logs. You can create graphs from the playtime and also export it as a csv file. 

~Due to the text encoding used, this will likely only work on Windows.~ I have tested it on ubuntu 20 and it worked through wine. 

### There are 3 modes:

1. Automatic (default)
2. Enter path(s)
3. Enter glob

1: Automatic trys to detect your logs in the normal minecraft folder 
`C:/Users/USER/AppData/Roaming/.minecraft/logs`

2: With this mode you can enter your own file paths
Separate multiple paths with pipes (vertical bar: | ).

3: With glob you can enter a glob to select multiple folders in a directory,
glob will basically select your path but also all the paths of any subdirectories that might exist in your spicified path and that match the glob
Separate multiple globs with pipes (vertical bar: | ). Make sure files don't overlap

Folders that start with period must be explicitly specified
(AppData/Roaming/.*/logs)

Glob-Example: To find all logs folders in all folders that start with . in AppData,
`C:/Users/USER/AppData/Roaming/.*/**`
This would select all the logs in .minecraft but also in .technic for example.

Globs can take a bit to load if your selection is large.

You can read more about globs [here](https://pymotw.com/3/glob/).


This is how it all looks:

![Program GUI](https://i.imgur.com/UDoV2pC.png)

![A minecraft playtime graph](https://i.imgur.com/Og3PXvG.png)

---

## Results
You can export the results into 2 ways
- A graph with hours per month
- A csv file with hours per session

## False positives
If you use the .exe file you might get a false positive with virus programs. I used pyinstaller to create a .exe from the .pyw file. I used this command to build the .exe 

This next part is only for those who use the .pyw version
---
At least python 3.6 is required for this program to work it might work on python 3.5, but I have not tested that.

(I now added python 3.7 and 3.8 support)

This program uses matplotlib pyplot to create graphs. If you do not have matplotlib installed please install it by entering the flowing command into the cmd:
`pip install --user matplotlib`

If that does not work try to reinstall python and make sure to click the install pip option.

The program will also detect if you do not have matplotlib installed, and it will ask you if you want to auto install.
This will basically run `os.system("pip install --user matplotlib")` this is the same as running `pip install --user matplotlib` in the cmd.

## Authors:
- Hawkpath (hawkpathas@gmail.com)
- Quinten (tintin10q@hotmail.com)

### Contributors

- @Phanabani Phanabani Phana
- @kwak0 kwak0
