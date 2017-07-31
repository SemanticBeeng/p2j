# coding=utf-8
"""     
        Written By:
                Chris Humphreys
                Email: < chris (--AT--) habitualcoder [--DOT--] com >
                Jan Weiß
                Email: < jan (--AT--) geheimwerk [--DOT--] de >

        Copyright 2010 Chris Humphreys
        Copyright 2012-2013 Jan Weiß
 
        This program is free software; you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation; either version 3 of the License, or
        (at your option) any later version.
 
        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.
 
        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <http://www.gnu.org/licenses/>.
 """

import ast
import os
import sys
from args import ArgTrace

from parser import *

TRACE_FILE_EXT = '.trace'
TRACE_RETURN_FILE_EXT = '.return-trace'

USE_RELATIVE_SOURCE_FILE_PATHS = True


def translate_files(input_filename):
    pathname = os.getcwd() + "/" + input_filename

    # load argument trace file
    args = ArgTrace.load_trace_files(input_filename, TRACE_FILE_EXT, TRACE_RETURN_FILE_EXT, USE_RELATIVE_SOURCE_FILE_PATHS)

    f = open(pathname)
    code = f.read()
    path = "target/" + input_filename[0:input_filename.find('.')]

    try:
        os.mkdir(path)
    except:
        pass

        # pathname = os.path.abspath(input_filename)
    p = Parser(args, pathname)
    e = OutputEmitter(path)
    e.enable_indentation(True)
    p.parse(code, e)
    e.finish()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Syntax: translate <input.py>")
        sys.exit(1)

    translate_files(sys.argv[1])
