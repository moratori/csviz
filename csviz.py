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
CSV_SPLITTER = ","



def make_dropdown_menu(path):

    """
    path 配下に存在する csv ファイル名からdropdown のメニューを作成する
    """

    files = os.listdir(path)
    if not files:
        print("there are no datafiles to show")
        sys.exit(1)

    return [{"label": fname, "value": fname} for fname in files]


def csv_header_check(headers):

    """
    csvファイルのヘッダ部分をチェックする
    headers の各行が COMMENT で始まるかを確認する
    """

    for line in headers:
        if not line:
            return False
        if line[0] != HEADER_COMMENT:
            return False
    return True


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



class GraphTypes(Enum):

    """
    サポートするグラフの形状一覧
    """

    Bar = auto()
    Scatter = auto()
    Lines = auto()


class Graph(object):

    """
    グラフを描画するために必要な諸々の情報を保持するクラス
    """

    GraphTypeIdentifier = {
        "lines"  : GraphTypes.Lines,
        "bar"    : GraphTypes.Bar,
        "scatter": GraphTypes.Scatter
    }

    def __init__(self, splitter):

        self.graph_title = ""
        self.xaxis_title = ""
        self.yaxis_title = ""
        self.graph_type = None
        self.CSVSplitChar = splitter

        self.x_data = ""

        self.column_title = []
        self.column_datum = []

    def __add_column(self, column_title, column_data):

        """
        column_title 列の名前
        column_data  データを表すリスト
        """

        self.column_title.append(column_title)
        self.column_datum.append(column_data)


    def load_dataset_file(self, file_path):

        """
        CSVファイルを読み込み、データをセットする

        想定するCSVファイルは初めの5行にコメントがある
        コメントはグラフのメタ情報を表す
        """

        with open(file_path, "r") as handle:

            title = handle.readline().strip()
            xaxis_title = handle.readline().strip()
            yaxis_title = handle.readline().strip()
            graph_type = handle.readline().strip()
            column_name = handle.readline().strip()

            if not csv_header_check([
                title,
                xaxis_title,
                yaxis_title,
                graph_type,
                column_name]): return

            self.graph_title = title[1:].strip()
            self.xaxis_title = xaxis_title[1:].strip()
            self.yaxis_title = yaxis_title[1:].strip()

            stripped = graph_type[1:].strip()

            if not stripped in self.GraphTypeIdentifier:
                return

            self.graph_type = self.GraphTypeIdentifier[stripped]

            column_title_row = list(map(lambda x: x.strip(),
                                        column_name[1:].split(self.CSVSplitChar)))
            tmp_data = []
            x = []

            for line in handle:
                st = line.strip()
                if st == "":
                    break
                row = st.split(self.CSVSplitChar)

                if len(row) != len(column_title_row):
                    return

                numrow = list(map(numstr_to_num, row))
                tmp_data.append(numrow)
                x.append(numrow[0])

            self.x_data = x

            trans = list(map(list, zip(*tmp_data)))[1:]
            name = list(column_title_row)[1:]

            for colname, colval in zip(name, trans):
                self.__add_column(colname, colval)



    def make_graph(self):

        """
        self.graph_type の値に応じて
        実際にグラフを作成するメソッドを呼び出す
        """

        if self.graph_type is None:
            return None

        if self.graph_type == GraphTypes.Bar:
            fig = self.__make_bar_chart()
        elif self.graph_type == GraphTypes.Lines:
            fig = self.__make_linear_chart()
        elif self.graph_type == GraphTypes.Scatter:
            fig = self.__make_scatter_chart()

        return fig

    def __make_bar_chart(self):

        """
        棒グラフを作る
        """

        traces = []

        for column_title, column_data in zip(self.column_title, self.column_datum):
            traces.append(
                go.Bar(
                    x=self.x_data,
                    y=column_data,
                    name=column_title))

        figure = {
            "data"  : traces,
            "layout": go.Layout(title=self.graph_title,
                                barmode="group",
                                xaxis={"title": self.xaxis_title},
                                yaxis={"title": self.yaxis_title})}

        return figure

    def __make_linear_chart(self):

        """
        線形のグラフを作る
        """

        traces = []

        for column_title, column_data in zip(self.column_title, self.column_datum):
            traces.append(
                go.Scatter(
                    x=self.x_data,
                    y=column_data,
                    mode="lines",
                    name=column_title))

        figure = {
            "data"  : traces,
            "layout": go.Layout(title=self.graph_title,
                                xaxis={"title": self.xaxis_title},
                                yaxis={"title": self.yaxis_title})}

        return figure

    def __make_scatter_chart(self):

        """
        散布図を作る
        """

        traces = []

        for column_title, column_data in zip(self.column_title, self.column_datum):
            traces.append(
                go.Scatter(
                    x=self.x_data,
                    y=column_data,
                    mode="markers",
                    name=column_title))

        figure = {
            "data"  : traces,
            "layout": go.Layout(title=self.graph_title,
                                xaxis={"title": self.xaxis_title},
                                yaxis={"title": self.yaxis_title})}

        return figure



argparser = argparse.ArgumentParser()
argparser.add_argument("directory", type=str, help="directory that contains csv file to show")
argparser.add_argument("--addr", type=str, help="ip address to bind")
argparser.add_argument("--port", type=int, help="port number to bind")
args = argparser.parse_args()

addr = "0.0.0.0" if not args.addr else args.addr
port = 8050 if not args.port else args.port
DIRECTORY = args.directory

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
    doc.Graph(id="graph", style={"height": 562, "width": 1000, "margin": "auto"})],
)


@application.callback(
    Output("graph", "figure"),
    [Input("graph_selection", "value")])
def update_graph(value):

    """
    指定ディレクトリ配下のCSVファイルを読み込み、グラフを描画する
    """

    if (value is None ) or (".." in value) or ("/" in value):
        return

    graph = Graph(CSV_SPLITTER)
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


application.run_server(debug=True, host=addr, port=port)

