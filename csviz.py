#!/usr/bin/env python3
#coding:utf-8

from enum import Enum, auto
import sys
import os
import socket
import argparse

import dash
import dash_html_components as html
import dash_core_components as doc
import plotly.graph_objs as go
from dash.dependencies import Input, Output

HEADER_COMMENT = "#"

def make_dropdown_menu(path):

    """
    path 配下に存在する csv ファイル名からdropdown のメニューを作成する
    """

    files = os.listdir(path)
    if not files:
        sys.exit(1)

    return [{"label": fname, "value": fname} for fname in files]



def numstr_to_num(numstr):

    """
    CSVファイル中の、数を表す文字列をPythonの数オブジェクトに変換する
    """

    try:
        int_val = int(numstr)
        float_val = float(numstr)
        if "." in numstr:
            return float_val
        return int_val
    except:
        return str(numstr)



class Graph(object):

    """
    グラフを描画するために必要な諸々の情報を保持するクラス
    """

    GraphTypeIdentifier = \
        {"lines"   : (lambda title,x,y: 
                        go.Scatter(x=x, y=y, mode="lines", name=title)),\
         "bar"     : (lambda title,x,y: 
                        go.Bar(x=x, y=y, name=title)),\
         "scatter" : (lambda title,x,y: 
                        go.Scatter(x=x, y=y, mode="markers", name=title))}

    def __init__(self, splitter, font_size):

        self.place_holder = "_"

        self.graph_title = ""
        self.xaxis_title = ""
        self.yaxis_title = ""
        self.graph_types = []
        self.CSVSplitChar = splitter
        self.font_size = font_size

        self.x_data = []

        self.column_title = []
        self.column_datum = []

    def __csv_header_check(self, headers):
    
        """
        csvファイルのヘッダ部分をチェックする
        headers の各行が COMMENT で始まるかを確認する
        """
    
        for line in headers:
            if not line:
                return False
            if line[0] != HEADER_COMMENT:
                return False
            if len(line.strip()) == 1:
                return False

        return True

    def __parse_graph_types(self, graph_types):

        tmp = \
            [typ.strip() for typ in graph_types[1:].strip().lower().split(self.CSVSplitChar)]


        for i,typ in enumerate(tmp):
            if len(tmp) > 1 and i == 0 and typ != self.place_holder:
                return
            if typ == self.place_holder: continue
            if not typ in self.GraphTypeIdentifier:
                return

        if len(tmp) == 1:
            return tmp
        else:
            return tmp[1:]


    def __parse_column_title(self, column_name):


        column_title_row = \
            [x.strip() for x in column_name[1:].split(self.CSVSplitChar)]

        if len(self.graph_types) > 1 and len(column_title_row) != len(self.graph_types) + 1:
            return

        if len(column_title_row) < 2:
            return

        return column_title_row[1:]



    def load_dataset_file(self, file_path):

        """
        CSVファイルを読み込み、データをセットする

        想定するCSVファイルは初めの5行にコメントがある
        コメントはグラフのメタ情報を表す
        """

        with open(file_path, "r") as handle:

            title       = handle.readline().strip()
            xaxis_title = handle.readline().strip()
            yaxis_title = handle.readline().strip()
            graph_types = handle.readline().strip()
            column_name = handle.readline().strip()

            if not self.__csv_header_check([
                title,
                xaxis_title,
                yaxis_title,
                graph_types,
                column_name]): return

            self.graph_title = title[1:].strip()
            self.xaxis_title = xaxis_title[1:].strip()
            self.yaxis_title = yaxis_title[1:].strip()
            self.graph_types = self.__parse_graph_types(graph_types)

            if not self.graph_types:
                return


            self.column_title = self.__parse_column_title(column_name)

            if not self.column_title:
                return

            if len(self.graph_types) < len(self.column_title):
                specific_type = self.graph_types[0]
                larger  = len(self.column_title)
                smaller = len(self.graph_types)
                self.graph_types.extend([specific_type] * (larger - smaller))
            elif len(self.graph_types) > len(self.column_title):
                return

            tmp_data = []
            x = []

            for line in handle:
                st = line.strip()
                if st == "":
                    break
                row = st.split(self.CSVSplitChar)

                if len(row) != len(self.column_title) + 1:
                    return

                numrow = list(map(numstr_to_num, row))
                tmp_data.append(numrow)
                x.append(numrow[0])

            trans = list(map(list, zip(*tmp_data)))[1:]

            self.x_data = x
            self.column_datum = trans



    def make_graph(self):

        """
        self.graph_type の値に応じて
        実際にグラフを作成するメソッドを呼び出す
        """

        if not self.graph_types:
            return

        traces = []


        for graph_type, column_title, column_data in zip(self.graph_types, self.column_title, self.column_datum):
            trace_maker = self.GraphTypeIdentifier[graph_type]
            trace = trace_maker(column_title, self.x_data, column_data)
            traces.append(trace)

        figure = {
            "data"  : traces,
            "layout": go.Layout(title=self.graph_title,
                                xaxis={"title": self.xaxis_title},
                                yaxis={"title": self.yaxis_title},
                                font={"size":self.font_size})}


        return figure



argparser = argparse.ArgumentParser()
argparser.add_argument("directory", type=str, help="directory that contains csv file to show")
argparser.add_argument("--addr", type=str, default="0.0.0.0", help="ip address to bind")
argparser.add_argument("--port", type=int, default=8050, help="port number to bind")
argparser.add_argument("--width", type=int, default=1080, help="width for graph")
argparser.add_argument("--height", type=int, default=550, help="height for graph")
argparser.add_argument("--delimiter", type=str, default=",", help="csv delimitor")
argparser.add_argument("--fontsize", type=int, default=17, help="font size")
args = argparser.parse_args()

DIRECTORY = args.directory
CSV_SPLITTER = args.delimiter
FONT_SIZE = args.fontsize

if not os.path.isdir(DIRECTORY):
    print("directory does not exist")
    sys.exit(1)

menu = make_dropdown_menu(DIRECTORY)

application = dash.Dash()
application.layout = html.Div([
    html.H1("統計情報"),
    html.H4("データ読み込み先ディレクトリ: %s" %(DIRECTORY + "@" + socket.gethostname())),
    doc.Dropdown(
        id="graph_selection",
        options=menu,
        value=menu[0]["value"],
        multi=False),
    html.Button("更新", id="update-menu"),
    doc.Graph(id="graph", style={"height": args.height, "width": args.width, "margin": "auto"})],)


@application.callback(
    Output("graph", "figure"),
    [Input("graph_selection", "value")])
def update_graph(value):

    """
    指定ディレクトリ配下のCSVファイルを読み込み、グラフを描画する
    """

    if (not value) or (".." in value) or ("/" in value):
        return

    graph = Graph(CSV_SPLITTER, FONT_SIZE)
    graph.load_dataset_file(os.path.join(DIRECTORY, value))

    return graph.make_graph()


@application.callback(
    Output("graph_selection", "options"),
    [Input("update-menu", "n_clicks")])
def update_menu(_):

    """
    指定ディレクトリ配下のファイルから、ドロップダウンメニューを再作成する
    """

    return make_dropdown_menu(DIRECTORY)


application.run_server(debug=True, host=args.addr, port=args.port)

