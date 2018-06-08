# CSVIZ; A Simple CSV data Visualizer

![sample-image1](https://mtcq.jp/images/3737459363.jpeg)

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
   (csviz) $ python csviz.py directory
   ```

3. access to __localhost__:8050

   ![sample-image2](https://mtcq.jp/images/3735713966.jpeg)

## Options

- --addr "0.0.0.0": ip address to bind
- --port 8050: port number to bind
- --width 1080: width for graph
- --height 550: height for graph
- --delimiter ",": delimiter for csv
- --fontsize 17: font size
- --bgcolor "ffe": graph baclground color
- --apptitle "Statistical Information for Something System": title of app
- --debug : debug mode
- --showtoolbar : show flooting tool bar
- --offline: disable loading resources from CDN

## Demo

[https://stats.mtcq.jp/](https://stats.mtcq.jp/)
