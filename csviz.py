#!/usr/bin/env python3
#coding:utf-8

import sys
import os
import socket
import argparse
import datetime
import dash
import dash_html_components as html
import dash_core_components as doc
import plotly.graph_objs as go
from dash.dependencies import Input, Output


class Graph(object):

    """
    グラフを描画するために必要な諸々の情報を保持するクラス
    """

    GraphTypeIdentifier = \
        {"lines"   : (lambda title,x,y,axis: 
                        go.Scatter(x=x, y=y, mode="lines", name=title, yaxis=axis)),\
         "bar"     : (lambda title,x,y,axis: 
                        go.Bar(x=x, y=y, name=title, yaxis=axis)),\
         "scatter" : (lambda title,x,y,axis: 
                        go.Scatter(x=x, y=y, mode="markers", name=title, yaxis=axis))}

    Y2_INDICATES = "%"
    PLACE_HOLDER = "_"
    HEADER_COMMENT = "#"

    def __init__(self, splitter, font_size, bgcolor):

        self.graph_title = ""
        self.xaxis_title = ""
        self.yaxis_title = []
        self.graph_types = []
        self.CSVSplitChar = splitter
        self.font_size = font_size
        self.bgcolor = bgcolor

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
            if line[0] != self.HEADER_COMMENT:
                return False
            if len(line.strip()) == 1:
                return False

        return True

    def __numstr_to_num(self, numstr):
    
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



    def __parse_graph_types(self, graph_types):

        tmp = \
            [typ.strip() for typ in graph_types[1:].strip().lower().split(self.CSVSplitChar)]


        for i,typ in enumerate(tmp):
            if len(tmp) > 1 and i == 0 and typ != self.PLACE_HOLDER:
                return
            if typ == self.PLACE_HOLDER: continue
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
            self.yaxis_title = [x.strip() for x in yaxis_title[1:].strip().split(self.CSVSplitChar)]
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

                numrow = list(map(self.__numstr_to_num, row))
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

            if column_title == self.Y2_INDICATES:
                return

            if column_title.startswith(self.Y2_INDICATES):
                if len(self.yaxis_title) == 1:
                    return
                axis = "y2"
                column_title = column_title[1:]
            else:
                axis = "y1"

            trace_maker = self.GraphTypeIdentifier[graph_type]
            trace = trace_maker(column_title, self.x_data, column_data, axis)
            traces.append(trace)

        if len(self.yaxis_title) == 1:
            yaxis2 = {}
        else:
            yaxis2 = {"title": self.yaxis_title[1], "side":"right", "overlaying":"y"}

        figure = {
            "data"  : traces,
            "layout": go.Layout(title=self.graph_title,
                                xaxis={"title": self.xaxis_title},
                                yaxis={"title": self.yaxis_title[0]},
                                yaxis2=yaxis2,
                                paper_bgcolor=self.bgcolor,
                                plot_bgcolor=self.bgcolor,
                                font={"size":self.font_size},
                                legend={"orientation":"h", "font": {"size": int(0.85 * self.font_size)},
                                        "yanchor":"top"})}

        return figure



def make_dropdown_menu(path):

    """
    path 配下に存在する csv ファイル名からdropdown のメニューを作成する
    """

    files = os.listdir(path)
    if not files:
        print("directory does not contain any files")
        sys.exit(1)

    return [{"label": fname, "value": fname} for fname in files]


def setup_command_line_argument_parser():

    argparser = argparse.ArgumentParser()
    argparser.add_argument("directory", type=str, help="directory that contains csv file to show")
    argparser.add_argument("--addr", type=str, default="0.0.0.0", help="ip address to bind")
    argparser.add_argument("--port", type=int, default=8050, help="port number to bind")
    argparser.add_argument("--width", type=int, default=1080, help="width for graph")
    argparser.add_argument("--height", type=int, default=590, help="height for graph")
    argparser.add_argument("--delimiter", type=str, default=",", help="csv delimitor")
    argparser.add_argument("--fontsize", type=int, default=14, help="font size")
    argparser.add_argument("--bgcolor", type=str, default="ffe", help="font size")
    argparser.add_argument("--apptitle", type=str,default="Statistical Information for Something System", help="application title")
    argparser.add_argument("--graphcache", type=int, default=5, help="caching time for graph object")
    args = argparser.parse_args()

    return args



if __name__ == "__main__":
    args = setup_command_line_argument_parser()

    if not os.path.isdir(args.directory):
        print("directory does not exist")
        sys.exit(1)

    GraphCache = {}

    menu = make_dropdown_menu(args.directory)

    application = dash.Dash()
    application.layout = html.Div([
        html.H1(args.apptitle),
        html.H4("loading from: %s" %(args.directory + "@" + socket.gethostname())),
        doc.Dropdown(
            id="graph_selection",
            options=menu,
            value=menu[0]["value"],
            multi=False),
        html.Button("reload file list", id="update-menu"),
        doc.Graph(id="graph", style={"height": args.height, "width": args.width, "margin": "auto"}),
        html.H3("Raw Data Table"),
        html.Table(id="rawdata", style={"margin":"auto", "textAlign":"center", "bgcolor":"#ffffee"})
    ],)


    @application.callback(
        Output("graph", "figure"),
        [Input("graph_selection", "value")])
    def update_graph(value):

        """
        指定ディレクトリ配下のCSVファイルを読み込み、グラフを描画する
        """

        if (not value) or (".." in value) or ("/" in value):
            return

        current_time = datetime.datetime.now()
        cache = GraphCache.get(value, None)
        isold = True if not cache else (current_time - cache[0]) > datetime.timedelta(seconds=args.graphcache)

        if isold:
            graph = Graph(args.delimiter, args.fontsize, "#" + args.bgcolor)
            graph.load_dataset_file(os.path.join(args.directory, value))
            GraphCache[value] = (current_time, graph)
        else:
            graph = cache[1]

        return graph.make_graph()

    @application.callback(
        Output("rawdata", "children"),
        [Input("graph_selection", "value")])
    def update_table(value):

        if (not value) or (".." in value) or ("/" in value):
            return

        current_time = datetime.datetime.now()
        cache = GraphCache.get(value, None)
        isold = True if not cache else (current_time - cache[0]) > datetime.timedelta(seconds=args.graphcache)

        if isold:
            graph = Graph(args.delimiter, args.fontsize, "#" + args.bgcolor)
            graph.load_dataset_file(os.path.join(args.directory, value))
            GraphCache[value] = (current_time, graph)
        else:
            graph = cache[1]

        contents = []
        contents.append(html.Tr([html.Th("_")]  + [html.Th(each) for each in graph.column_title]))

        for i, row in enumerate(list(map(list, zip(*graph.column_datum)))):
            contents.append(html.Tr([html.Td(graph.x_data[i])] + [html.Td(x) for x in row]))

        return contents

    @application.callback(
        Output("graph_selection", "options"),
        [Input("update-menu", "n_clicks")])
    def update_menu(_):

        """
        指定ディレクトリ配下のファイルから、ドロップダウンメニューを再作成する
        """

        return make_dropdown_menu(args.directory)

    application.run_server(debug=True, host=args.addr, port=args.port)

