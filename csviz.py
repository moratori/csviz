#!/usr/bin/env python3
#coding:utf-8

import sys
import os
import argparse
import hashlib
import logging
import logging.handlers
from abc import ABCMeta, abstractmethod
from enum import Enum, auto
from flask import abort, Response

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
    argparser.add_argument("--width", type=int, default=1300, help="width for graph")
    argparser.add_argument("--height", type=int, default=590, help="height for graph")
    argparser.add_argument("--delimiter", type=str, default=",", help="csv delimitor")
    argparser.add_argument("--fontsize", type=int, default=14, help="font size")
    argparser.add_argument("--bgcolor", type=str, default="ffe", help="font size")
    argparser.add_argument("--apptitle", type=str,default="Statistical Information for Something System", help="application title")
    argparser.add_argument("--debug", action="store_true", help="setting for debug mode")
    argparser.add_argument("--showtoolbar", action="store_true", help="show flooting toolbar")
    argparser.add_argument("--offline", action="store_true", help="disable loading resources from cdn")
    argparser.add_argument("--log", type=str, default=None, help="log file name")
    argparser.add_argument("--cssdir", type=str, default=None, help="css directory")

    args = argparser.parse_args()

    return args


def setup_logging(log_file_path):

    global LOGGER

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s :: %(message)s")

    if log_file_path is None:
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


class GraphTypes(Enum):

    Lines = auto()
    Bar = auto()
    Scatter = auto()


class GraphDatum(object):

    def __init__(self):

        self.graph_title = ""
        self.xaxis_title = ""
        self.xaxis_slider = False
        self.yaxis_title = []
        self.graph_types = []
        self.font_size = 0
        self.bgcolor = ""

        self.x_data = []
        self.column_title = []
        self.column_datum = []


class DataLoader(metaclass=ABCMeta):

    @abstractmethod
    def setup_load(self):
        pass

    @abstractmethod
    def load(self):
        pass


class CSVFileLoader(DataLoader):

    Y2_INDICATES = "%"
    PLACE_HOLDER = "_"
    HEADER_COMMENT = "#"
    RANGESLIDER = "rangeslider"
    SUBCOMMAND_SEP = ":"
    GRAPH_TYPES_CONVERTER = {"lines"  : GraphTypes.Lines, 
                             "bar"    : GraphTypes.Bar, 
                             "scatter": GraphTypes.Scatter}

    def __init__(self, filepath, delimiter):
        self.filepath  = filepath
        self.delimiter = delimiter
        self.datum = GraphDatum()

    def __csv_header_check(self, headers):
    
        for line in headers:
            if not line:
                LOGGER.warn("empty line found while header")
                return False
            if line[0] != self.HEADER_COMMENT:
                LOGGER.warn("assumed comment character for header does not exist \"%s\"" %str(line[0]))
                return False
            if len(line.strip()) == 1:
                LOGGER.warn("too short hedaer line")
                return False

        return True

    def __numstr_to_num(self, numstr):

        try:
            int_val = int(numstr)
            float_val = float(numstr)
            if "." in numstr:
                return float_val
            return int_val
        except:
            return str(numstr)

    def __parse_graph_types(self, graph_types):

        tmp = [typ.strip() for typ in graph_types[1:].strip().lower().split(self.delimiter)]

        for i,typ in enumerate(tmp):
            if len(tmp) > 1 and i == 0 and typ != self.PLACE_HOLDER:
                LOGGER.warn("when specifying more than one graph type, first type must be place holder")
                return
            if typ == self.PLACE_HOLDER: continue
            if not typ in self.GRAPH_TYPES_CONVERTER:
                LOGGER.warn("unrecognized graph type \"%s\"" %str(typ))
                return

        return (tmp if len(tmp) == 1 else tmp[1:])

    def __parse_column_title(self, column_name):

        column_title_row = []

        for each in column_name[1:].split(self.delimiter):
            clean = each.strip()

            if clean == self.Y2_INDICATES:
                LOGGER.warn("invalid column title \"%s\"" %str(clean))
                return

            column_title_row.append((clean.startswith(self.Y2_INDICATES),clean))

        if len(self.datum.graph_types) > 1 and len(column_title_row) != len(self.datum.graph_types) + 1:
            LOGGER.warn("unmatch length for graph types and column titles")
            return

        if len(column_title_row) < 2:
            LOGGER.warn("too short column title, must greater than 2")
            return

        return column_title_row[1:]

    def __parse_xaxis_title(self, xaxis_title):

        if self.SUBCOMMAND_SEP in xaxis_title:
            flag = False
            title = ""
            first_half, last_half = [each.strip() for each in xaxis_title.split(self.SUBCOMMAND_SEP)]
            if last_half == self.RANGESLIDER:
                flag = True
                title = first_half
            else:
                title = xaxis_title
            return flag, title
        else:
            return False, xaxis_title

    def setup_load(self):
        pass

    def load(self):

        with open(self.filepath, "r") as handle:

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

            self.datum.graph_title = title[1:].strip()
            self.datum.xaxis_slider, self.datum.xaxis_title = self.__parse_xaxis_title(xaxis_title[1:].strip())
            self.datum.yaxis_title = [x.strip() for x in yaxis_title[1:].strip().split(self.delimiter)]
            self.datum.column_title = self.__parse_column_title(column_name)
            graph_types_pre_obj  = self.__parse_graph_types(graph_types)

            if graph_types_pre_obj is None:
                return

            if self.datum.column_title is None:
                return

            if len(graph_types_pre_obj) < len(self.datum.column_title):
                specific_type = graph_types_pre_obj[0]
                larger  = len(self.datum.column_title)
                smaller = len(graph_types_pre_obj)
                graph_types_pre_obj.extend([specific_type] * (larger - smaller))
            elif len(graph_types_pre_obj) > len(self.datum.column_title):
                return

            self.datum.graph_types = [self.GRAPH_TYPES_CONVERTER[each] for each in graph_types_pre_obj]

            tmp_data = []
            x = []

            for line in handle:
                st = line.strip()
                if st == "":
                    LOGGER.info("skip loading for empty line")
                    continue
                row = st.split(self.delimiter)

                if len(row) != len(self.datum.column_title) + 1:
                    return

                numrow = list(map(self.__numstr_to_num, row))
                tmp_data.append(numrow)
                x.append(numrow[0])

            trans = list(map(list, zip(*tmp_data)))[1:]

            self.datum.x_data = x
            self.datum.column_datum = trans

        return self.datum


class GraphMaker(object):

    TraceMaker = {GraphTypes.Lines   : (lambda title,x,y,axis: 
                                        go.Scatter(x=x, y=y, mode="lines", name=title, yaxis=axis)),\
                  GraphTypes.Bar     : (lambda title,x,y,axis: 
                                        go.Bar(x=x, y=y, name=title, yaxis=axis)),\
                  GraphTypes.Scatter : (lambda title,x,y,axis: 
                                        go.Scatter(x=x, y=y, mode="markers", name=title, yaxis=axis))}

    def __init__(self, datum, font_size, bgcolor):

        self.datum = datum
        self.font_size = font_size
        self.bgcolor = bgcolor

    def make_graph(self):

        if not self.datum.graph_types:
            return

        traces = []

        for graph_type, (y2flag, column_title), column_data in zip(self.datum.graph_types, 
                                                                   self.datum.column_title, 
                                                                   self.datum.column_datum):
            if y2flag:
                if len(self.datum.yaxis_title) == 1:
                    LOGGER.warn("y2 title must be specified")
                    return
                axis = "y2"
                column_title = column_title[1:]
            else:
                axis = "y1"

            trace_maker = self.TraceMaker[graph_type]
            trace = trace_maker(column_title, self.datum.x_data, column_data, axis)
            traces.append(trace)

        if len(self.datum.yaxis_title) == 1:
            yaxis2 = dict()
        else:
            yaxis2 = dict(title = self.datum.yaxis_title[1], side = "right", overlaying = "y")

        figure = dict(
            data = traces,
            layout = go.Layout(title=self.datum.graph_title,
                                xaxis=({"title": self.datum.xaxis_title} if not self.datum.xaxis_slider else
                                       {"title": self.datum.xaxis_title, "rangeslider":{}}),
                                yaxis=dict(title = self.datum.yaxis_title[0]),
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
    
    if not os.path.isdir(path):
        LOGGER.critical("csv data directory %s does not exist" %path)
        sys.exit(1)

    files = sorted(os.listdir(path))
    con = [dict(label = fname, value = fname) for fname in files if not fname.startswith(".")]

    if not con:
        LOGGER.critical("directory %s does not contain any files" %path)
        sys.exit(1)

    return con


def make_graph_wrapper(args, fname, listup=0):

    if listup > 0:
        graph_width  = args.width/listup
        graph_height = args.height
    else:
        graph_width = args.width
        graph_height = args.height

    try:
        loader = CSVFileLoader(os.path.join(args.directory, fname), args.delimiter)
        loader.setup_load()
        datum  = loader.load()
    except Exception as ex:
        LOGGER.error("exception occurred while loading data for \"%s\"" %fname)
        LOGGER.error("%s" %str(ex))
        return 

    if datum is None:
        LOGGER.warn("unable to load data for \"%s\"" %fname)
        return

    try:
        graph = GraphMaker(datum, args.fontsize, "#" + args.bgcolor)
        graph_obj = doc.Graph(id=hashlib.md5(fname.encode("utf-8")).hexdigest(),
                              figure=graph.make_graph(),
                              style=dict(height = graph_height, 
                                         width=graph_width, 
                                         marginTop= "18px",
                                         marginLeft="auto",
                                         marginRight="auto"),
                              config=dict(displayModeBar=args.showtoolbar))
        return graph_obj

    except Exception as ex:
        LOGGER.error("exception occurred while rendering graph for \"%s\"" %fname)
        LOGGER.error("%s" %str(ex))
        return



def add_local_css_to_app(cssdir):

    if cssdir is None:
        LOGGER.info("no external css directory specified")
        return

    if not os.path.isdir(cssdir):
        LOGGER.critical("csv data directory %s does not exist" %cssdir)
        sys.exit(1)

    tmp = os.listdir(cssdir)

    return [html.Link(rel="stylesheet", href="/css/%s" %each) 
            for each in tmp if each.endswith(".css")]


def make_header_links(pager):
    result = []
    for key in pager:
        (title, ref)= pager[key]
        result.append(html.Li(doc.Link(title, href=key)))
    return html.Ul(result)


def make_top_page(args, pager):

    menu = make_dropdown_menu(args.directory)

    return \
        html.Div([

        html.Div(add_local_css_to_app(args.cssdir)),

        html.Div([
            html.Div([
                make_header_links(pager)
            ],id="menu")
        ],id="header"),

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
                     boxShadow = "0px 0px 3px")),

        html.Div([],id="footer")])


def listup_graphs(args):

    files = make_dropdown_menu(args.directory)
    width_tiling = 2

    result = []
    width_graph_group = []

    for each in files:

        fname = each["value"]
        graph = make_graph_wrapper(args, fname, listup=width_tiling)

        graph_section = html.Div(graph, style=dict(width='%spx' %int(args.width/width_tiling),
                                                   display='inline-block',
                                                   marginRight="10px",
                                                   marginLeft="10px"))
        width_graph_group.append(graph_section)

        if len(width_graph_group) == width_tiling:
            result.append(html.Div(width_graph_group, style=dict(marginLeft="auto",marginRight="auto")))
            width_graph_group = []

    if width_graph_group:
        result.append(html.Div(width_graph_group, style=dict(marginLeft="auto",marginRight="auto")))

    return html.Div(result)



def make_graph_listup_page(args, pager):
    
    return \
        html.Div([
            
            html.Div(add_local_css_to_app(args.cssdir)),
            
            html.Div([
                html.Div([
                    make_header_links(pager)
                ],id="menu")
            ],id="header"),
            
            html.Div([
                html.H1("グラフ一覧", style=dict(textAlign="left")),
            ],style=dict(width=args.width+50,
                         fontFamily="Helvetica , 游ゴシック, sans-serif",
                         fontSize="18",
                         marginLeft="auto",
                         marginRight="auto")),
            
            html.Div([
                
                listup_graphs(args)
            
            ],style=dict(width=args.width+50, 
                         textAlign="center",
                         margin="auto",
                         paddingBottom="1%",
                         border="1px solid #eee",
                         boxShadow = "0px 0px 3px")),

            html.Div([],id="footer")])


if __name__ == "__main__":

    pager = {"/"     : ("トップ", make_top_page),
             "/list" : ("一覧", make_graph_listup_page)}

    args = setup_command_line_argument_parser()

    setup_logging(args.log)

    application = dash.Dash()
    application.title = args.apptitle
    application.css.config.serve_locally = args.offline
    application.scripts.config.serve_locally = args.offline

    application.layout = html.Div([
        doc.Location(id="url", refresh=False),
        html.Div([
            make_top_page(args,pager)
        ],id="page-content")])

    @application.callback(
        Output("graphs", "children"),
        [Input("graph_selection", "value")])
    def update_graph(value):

        graphs = []

        for each in reversed(value):

            LOGGER.info("loading for \"%s\"" %each)

            if (not each) or (".." in each) or ("/" in each):
                LOGGER.warn("invalid character \"%s\"" %each)
                continue

            graph_obj = make_graph_wrapper(args, each)

            if graph_obj is None:
                continue
            
            graphs.append(graph_obj)
            LOGGER.info("graph object collected in properly")

        return graphs

    @application.callback(
        Output("page-content", "children"),
        [Input("url","pathname")])
    def make_page(pathname):
        LOGGER.info("requested page \"%s\"" %pathname)

        if not pathname in pager:
            LOGGER.warn("requested page \"%s\" does not exists" %str(pathname))
            return

        title, maker = pager[pathname]

        return maker(args, pager)

    @application.callback(
        Output("graph_selection", "options"),
        [Input("update-menu", "n_clicks")])
    def update_menu(_):

        return make_dropdown_menu(args.directory)

    @application.server.route("/css/<stylesheet>")
    def serve_stylesheet(stylesheet):

        LOGGER.info("requested css file name \"%s\"" %str(stylesheet))

        if (".." in stylesheet) or ("/" in stylesheet):
            LOGGER.warn("invalid file name \"%s\"" %str(stylesheet))
            abort(404)

        try:
            with open(os.path.join(args.cssdir, stylesheet), "r") as handle:
                return Response(handle.read(), mimetype="text/css")

        except Exception as ex:
            LOGGER.warn("exception occurred while loading css file \"%s\"" %str(stylesheet))
            abort(404)

    application.run_server(debug=args.debug, host=args.addr, port=args.port)

