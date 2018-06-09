#!/usr/bin/env python3
#coding:utf-8

import sys
import os
import argparse
import hashlib
import logging
import logging.handlers

import dash
import dash_html_components as html
import dash_core_components as doc
import plotly.graph_objs as go
from dash.dependencies import Input, Output



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
    argparser.add_argument("--debug", action="store_true", help="setting for debug mode")
    argparser.add_argument("--showtoolbar", action="store_true", help="show flooting toolbar")
    argparser.add_argument("--offline", action="store_true", help="disable loading resources from cdn")
    argparser.add_argument("--log", type=str, default=None, help="log file name")

    args = argparser.parse_args()

    return args


def setup_logging(log_file_path):

    global LOGGER

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s :: %(message)s")

    if not log_file_path:
        handler = logging.StreamHandler()
    
    else:
        handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_file_path,
            when="D",
            backupCount=90)

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    LOGGER = logger

    return 



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
    RANGESLIDER = "rangeslider"

    def __init__(self, splitter, font_size, bgcolor):

        self.graph_title = ""
        self.xaxis_title = ""
        self.xaxis_slider = False
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

    def __parse_xaxis_title(self, xaxis_title):

        subcommand_sep = ":"

        if subcommand_sep in xaxis_title:
            flag = False
            title = ""
            first_half, last_half = [each.strip() for each in xaxis_title.split(subcommand_sep)]
            if last_half == self.RANGESLIDER:
                flag = True
                title = first_half
            else:
                title = xaxis_title
            return flag, title
        else:
            return False, xaxis_title



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
            self.xaxis_slider, self.xaxis_title = self.__parse_xaxis_title(xaxis_title[1:].strip())
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
                    continue
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
            yaxis2 = dict()
        else:
            yaxis2 = dict(title = self.yaxis_title[1], side = "right", overlaying = "y")

        figure = dict(
            data = traces,
            layout = go.Layout(title=self.graph_title,
                                xaxis=({"title": self.xaxis_title} if not self.xaxis_slider else
                                       {"title": self.xaxis_title,self.RANGESLIDER:{}}),
                                yaxis=dict(title = self.yaxis_title[0]),
                                yaxis2=yaxis2,
                                paper_bgcolor=self.bgcolor,
                                plot_bgcolor=self.bgcolor,
                                font=dict(size=self.font_size),
                                legend=dict(orientation = "h", 
                                            font = dict(size = int(0.85 * self.font_size)),
                                            yanchor="top",
                                            x=0,
                                            y=1.1)))

        return figure



def make_dropdown_menu(path):

    """
    path 配下に存在する csv ファイル名からdropdown のメニューを作成する
    """

    files = os.listdir(path)
    if not files:
        LOGGER.critical("directory %s does not contain any files" %path)
        sys.exit(1)

    return [dict(label = fname, value = fname) for fname in files if not fname.startswith(".")]



if __name__ == "__main__":

    args = setup_command_line_argument_parser()
    setup_logging(args.log)

    if not os.path.isdir(args.directory):
        LOGGER.critical("directory %s does not exist" %args.directory)
        sys.exit(1)

    menu = make_dropdown_menu(args.directory)

    application = dash.Dash()

    application.title = args.apptitle
    application.css.config.serve_locally = args.offline
    application.scripts.config.serve_locally = args.offline

    application.layout = html.Div([

        html.Div([
            html.H1(args.apptitle, style=dict(textAlign="left")),
        ],style=dict(width=args.width+50,
                     fontFamily="Helvetica , 游ゴシック, sans-serif",
                     fontSize="18",
                     marginLeft="auto",
                     marginRight="auto")),

        html.Div([

        html.Div([
        doc.Dropdown(
            id="graph_selection",
            options=menu,
            value=[menu[0]["value"]],
            multi=True),
        html.Button("reload list", id="update-menu")
        ],style=dict(width=args.width, 
                     marginLeft="auto",
                     marginRight="auto",
                     marginTop="2%")),

        html.Div(id="graphs")
        ],style=dict(width=args.width+50, 
                     margin="auto",
                     paddingBottom="1%",
                     border="1px solid #eee",
                     boxShadow = "0px 0px 3px"))])


    @application.callback(
        Output("graphs", "children"),
        [Input("graph_selection", "value")])
    def update_graph(value):

        """
        指定ディレクトリ配下のCSVファイルを読み込み、グラフを描画する
        """

        graphs = []

        for each in reversed(value):

            if (not each) or (".." in each) or ("/" in each):
                return

            graph = Graph(args.delimiter, args.fontsize, "#" + args.bgcolor)
            graph.load_dataset_file(os.path.join(args.directory, each))

            graph_obj = doc.Graph(id=hashlib.md5(each.encode("utf-8")).hexdigest(),
                                  figure=graph.make_graph(),
                                  style=dict(height = args.height, 
                                             width=args.width, 
                                             marginTop= "18px",
                                             marginLeft="auto",
                                             marginRight="auto"),
                                  config=dict(displayModeBar=args.showtoolbar))

            graphs.append(graph_obj)

        return graphs

    @application.callback(
        Output("graph_selection", "options"),
        [Input("update-menu", "n_clicks")])
    def update_menu(_):

        """
        指定ディレクトリ配下のファイルから、ドロップダウンメニューを再作成する
        """

        return make_dropdown_menu(args.directory)

    application.run_server(debug=args.debug, host=args.addr, port=args.port)

