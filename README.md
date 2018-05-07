# CSVIZ; A Simple CSV data Visualizer

## Installation

```shell
$ conda env create --file requirements.txt
```

## Usage

1. make a csv file like below and save file to __directory__.

   ```
   # this line is title for graph
   # this line is title for horizontal axis
   # this line is title for vertical axis
   # lines
   # _, series1, series2, series3
     0,       0,       0,      1 
     1,       1,       1,      2
     2,       2,       4,      4
     3,       3,       9,      8
     4,       4,      16,     16
     5,       5,      25,     32
   ```

2. run the script __csviz.py__ with argument __directory__

   ```
   (graph-test) $ python csviz.py directory
   ```

3. access to __localhost__:8050

## Options

- --addr: ip address to bind
- --port: port number to bind
- --width: width for graph
- --height: height for graph

## Demo

TBD

