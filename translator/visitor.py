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
from collections import deque
from types import *

from transbits import *

DEBUG = False


class ActiveStack():
    def __init__(self):
        self._active = deque()

    def pop(self):
        r = self._active.pop()
        if DEBUG: print("Popping %s " % r)

        return r

    def push(self, ob):
        if DEBUG: print("Pushing %s" % str(ob))

        self._active.append(ob)


    def peek(self):
        return self._active[-1]


    def size(self):
        return len(self._active)


class MyVisitor(ast.NodeVisitor):
    def __init__(self, arg_trace, python_filename):
        self.active = ActiveStack()
        self.arg_trace = arg_trace
        self.python_filename = python_filename
        self.function_stack = ActiveStack()
        self.return_types = dict()

    def visit_Str(self, node):
        if DEBUG: print("Found string %s" % node.s)

        java_str = JavaStr(node.s)
        java_str.set_metadata(node)
        self.active.push(java_str)


    def visit_Module(self, node):
        return ast.NodeVisitor.generic_visit(self, node)


    def my_generic_visit(self, node):
        if DEBUG:
            print("-----------node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
            # ast.NodeVisitor.generic_visit(self, node)
        self.visit(node)
        if DEBUG: print("-----------node-----------")


    def visit_ClassDef(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        start = self.active.size()
        self.iter_field(node.bases)
        base_end = self.active.size()
        if DEBUG: print("%d args" % (base_end - start))

        self.iter_field(node.body)
        end = self.active.size()
        if DEBUG: print("%d body nodes" % (end - base_end))
        body = JavaStatements()
        self.fill(body, end - base_end)
        args = JavaList()
        self.fill(args, base_end - start)
        java_class = JavaClass(node.name, args, body)
        java_class.set_metadata(node)
        self.active.push(java_class)
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_FunctionDef(self, node):
        if DEBUG:
            print("-----------start node  %s   -----------" % node.__class__.__name__)
            print(ast.dump(node, True, True))
        self.function_stack.push(node)
        start = self.active.size()
        self.iter_field(node.body)
        end = self.active.size()
        body = JavaStatements()
        self.fill(body, end - start)
        start = self.active.size()
        self.iter_field(node.args.args)
        end = self.active.size()
        args = JavaList()
        self.fill(args, end - start)
        # identify argument types...
        self.infer_arguments_types(node, args)
        java_func = JavaFunction(node.name, args, body)
        if node in self.return_types:
            return_types = self.return_types[node]
        else:
            return_types = None
        java_func.set_return_type(return_types)
        java_func.set_metadata(node)
        self.active.push(java_func)
        self.function_stack.pop()
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def infer_return_type(self, function_node, lineno):
        method_name = function_node.name
        type = self.arg_trace.find_return_type(self.python_filename, lineno, method_name)
        return type


    def infer_arguments_types(self, function_node, arguments):
        lineno = function_node.lineno
        method_name = function_node.name
        # print "Line no: %d method %s" % (lineno, method_name)
        if self.arg_trace:
            args = self.arg_trace.find_method_args(self.python_filename, lineno, method_name)
            for arg in arguments.list:
                arg_name = ""
                if isinstance(arg, JavaVariable):
                    arg_name = arg.name
                elif isinstance(arg, JavaTuple):
                    arg_name = "anonymous_list"

                if arg_name == "":
                    arg_name = "unknown_arg"
                    type = "unknown_type"
                else:
                    type = self.arg_trace.get_method_arg(args, arg_name)

                arg.set_type(type)
                print("argument %s type %s" % (arg_name, type))


    def visit_arguments(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        start = self.active.size()
        ast.NodeVisitor.generic_visit(self, node)
        end = self.active.size()
        arg_list = JavaList()
        self.fill(arg_list, end - start)
        self.active.push(arg_list)

        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_BinOp(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        ast.NodeVisitor.generic_visit(self, node)
        right = self.active.pop()
        op = self.active.pop()
        left = self.active.pop()
        java_bin_op = JavaBinOp(left, right, op)
        java_bin_op.set_metadata(node)
        self.active.push(java_bin_op)
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_Mult(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaMult())
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_Mod(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaMod())
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_Add(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaAdd())
        if DEBUG:
            print("----")
            print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_Div(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaDiv())
        if DEBUG:
            print("----")
            print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_Assign(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        ast.NodeVisitor.generic_visit(self, node)
        value = self.active.pop()
        target = self.active.pop()
        java_assign = JavaAssign(target, value)
        java_assign.set_metadata(node)
        self.active.push(java_assign)
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_AugAssign(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        ast.NodeVisitor.generic_visit(self, node)
        value = self.active.pop()
        op = self.active.pop()
        target = self.active.pop()
        java_assign = JavaAugAssign(target, value, op)
        java_assign.set_metadata(node)
        self.active.push(java_assign)
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_Tuple(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        start = self.active.size()
        ast.NodeVisitor.generic_visit(self, node)
        end = self.active.size()
        java_tuple = JavaTuple()
        if DEBUG: print("popping %d from stack" % (end - start))

        self.fill(java_tuple, end - start)
        java_tuple.set_metadata(node)
        self.active.push(java_tuple)
        if DEBUG: print("-----------end node  %s -----------" % node.__class__.__name__)


    def visit_Name(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print("%s = %s (%s)" % (node.__class__.__name__, node.id, node.ctx))
        java_var = JavaVariable(node.id, str(node.ctx))
        java_var.set_metadata(node)
        self.active.push(java_var)
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_Num(self, node):
        if DEBUG: print("-----------start node  %s -----------" % node.__class__.__name__)

        java_var = JavaNum(node.n)
        java_var.set_metadata(node)
        self.active.push(java_var)
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_Attribute(self, node):
        if DEBUG: print("-----------start node  %s -----------" % node.__class__.__name__)

        self.iter_field(node.value)
        val = self.active.pop()
        att = JavaAttribute(val, node.attr)
        att.set_metadata(node)
        self.active.push(att)
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def fill(self, obj, amt):
        reverse = deque()
        for i in range(0, amt):
            java = self.active.pop()
            reverse.append(java)
        while len(reverse) > 0:
            obj.add(reverse.pop())


    def visit_Load(self, node):
        pass


    def visit_Store(self, node):
        pass


    def visit_Compare(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
            # ast.NodeVisitor.generic_visit(self, node)
        self.iter_field(node.left)
        left = self.active.pop()
        self.iter_field(node.ops)
        ops = self.active.pop()
        self.iter_field(node.comparators)
        comparators = self.active.pop()
        comp = JavaCompare(left, ops, comparators)
        comp.set_metadata(node)
        self.active.push(comp)
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_BoolOp(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))

        java_tuple = JavaList()
        start = self.active.size()
        self.iter_field(node.values)
        end = self.active.size()
        self.fill(java_tuple, end - start)

        self.iter_field(node.op)
        op = self.active.pop()

        java_bool_op = JavaBoolOp(java_tuple, op)
        java_bool_op.set_metadata(node)
        self.active.push(java_bool_op)


    def visit_And(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaAnd())
        if DEBUG:
            print("----")
            print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_Gt(self, node):
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaGt())


    def visit_GtE(self, node):
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaGte())


    def visit_Lt(self, node):
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaLt())


    def visit_LtE(self, node):
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaLte())


    def visit_Or(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaOr())
        if DEBUG:
            print("----")
            print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_BitOr(self, node):
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaBitOr())


    def visit_BitXor(self, node):
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaBitXor())


    def visit_BitAnd(self, node):
        ast.NodeVisitor.generic_visit(self, node)
        self.active.push(JavaBitAnd())


    def visit_Call(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
            # ast.NodeVisitor.generic_visit(self, node)
        self.iter_field(node.func)
        func = self.active.pop()
        start = self.active.size()
        self.iter_field(node.args)
        end = self.active.size()
        arg_list = JavaList()
        self.fill(arg_list, end - start)
        java_call = JavaCall(func, arg_list)
        java_call.set_metadata(node)
        self.active.push(java_call)
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_If(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
            # ast.NodeVisitor.generic_visit(self, node)

        self.iter_field(node.test)
        test = self.active.pop()

        start = self.active.size()
        self.iter_field(node.body)
        end = self.active.size()
        body = JavaStatements()
        self.fill(body, end - start)

        start = self.active.size()
        self.iter_field(node.orelse)
        end = self.active.size()
        orelse = None
        if end - start > 0:
            orelse = JavaStatements()
            self.fill(orelse, end - start)

        java_if = JavaIf(test, body, orelse)
        java_if.set_metadata(node)
        self.active.push(java_if)
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_NotEq(self, node):
        self.active.push(JavaNotEq())


    def visit_NotIn(self, node):
        self.active.push(JavaNotIn())


    def visit_Not(self, node):
        self.active.push(JavaNot())


    def visit_In(self, node):
        self.active.push(JavaIn())


    def visit_Eq(self, node):
        self.active.push(JavaEq())


    def visit_Sub(self, node):
        self.active.push(JavaSub())


    def visit_List(self, node):
        start = self.active.size()
        self.iter_field(node.elts)
        end = self.active.size()
        contents = JavaStatements()
        self.fill(contents, end - start)

        self.active.push(JavaValueList(contents))


    def visit_Return(self, node):
        if node.value:
            self.iter_field(node.value)
            value = self.active.pop()
        else:
            value = None
        java_return = JavaReturn(value)

        function_node = self.function_stack.peek()
        if function_node in self.return_types:
            types_set = self.return_types[function_node]
        else:
            types_set = set()
            self.return_types[function_node] = types_set
        types_set |= self.infer_return_type(function_node, node.lineno)

        java_return.set_metadata(node)
        self.active.push(java_return)


    def visit_Subscript(self, node):
        self.iter_field(node.value)
        value = self.active.pop()
        self.iter_field(node.slice)
        jslice = self.active.pop()
        store = isinstance(node.ctx, ast.Store)
        obj = JavaSubscript(value, jslice, store)
        obj.set_metadata(node)
        self.active.push(obj)


    def visit_Pass(self, node):
        self.active.push(JavaPass())


    def visit_Print(self, node):
        self.iter_field(node.values)
        values = self.active.pop()
        obj = JavaPrint(values)
        obj.set_metadata(node)
        self.active.push(obj)


    def visit_Slice(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))

        self.iter_field(node.lower)
        lower = self.active.pop()
        if node.upper:
            self.iter_field(node.upper)
            upper = self.active.pop()
        else:
            upper = None
        if node.step:
            self.iter_field(node.step)
            step = self.active.pop()
        else:
            step = None
        self.active.push(JavaSlice(lower, upper, step))
        if DEBUG: print("-----------end node   %s -----------" % node.__class__.__name__)


    def visit_For(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        self.iter_field(node.target)
        target = self.active.pop()
        self.iter_field(node.iter)
        iterator = self.active.pop()

        start = self.active.size()
        self.iter_field(node.body)
        end = self.active.size()
        body = JavaStatements()
        self.fill(body, end - start)

        obj = JavaFor(target, iterator, body)
        obj.set_metadata(node)
        self.active.push(obj)


    def finish(self):
        body = JavaStatements()
        self.fill(body, self.active.size())
        return body


    def iter_field(self, field):
        if DEBUG: print("iter")

        if isinstance(field, ast.AST):
            if DEBUG: print("field %s" % field.__class__.__name__)
            # self.generic_visit(field)
            ast.NodeVisitor.visit(self, field)
        elif isinstance(field, list):
            if DEBUG: print("list")
            for item in field:
                if DEBUG:
                    print("field?")
                    print(item)
                    if isinstance(item, ast.AST):
                        if DEBUG: print(item.__class__.__name__)
                    self.my_generic_visit(item)


    def visit_UnaryOp(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))

        self.iter_field(node.operand)
        operand = self.active.pop()

        self.iter_field(node.op)
        op = self.active.pop()

        j = JavaUnaryOp(operand, op)
        j.set_metadata(node)
        self.active.push(j)


    def visit_USub(self, node):
        self.active.push(JavaUSub())


    def visit_UAdd(self, node):
        self.active.push(JavaUAdd())


    def visit_TryExcept(self, node):
        start = self.active.size()
        self.iter_field(node.body)
        end = self.active.size()
        body = JavaStatements()
        self.fill(body, end - start)

        start = self.active.size()
        self.iter_field(node.handlers)
        end = self.active.size()
        handlers = JavaStatements()
        self.fill(handlers, end - start)
        obj = JavaTryExcept(body, handlers)
        obj.set_metadata(node)
        self.active.push(obj)


    def visit_TryFinally(self, node):
        start = self.active.size()
        self.iter_field(node.body)
        end = self.active.size()
        body = JavaStatements()
        self.fill(body, end - start)

        start = self.active.size()
        self.iter_field(node.finalbody)
        end = self.active.size()
        handlers = JavaStatements()
        self.fill(handlers, end - start)
        obj = JavaTryFinally(body, handlers)
        obj.set_metadata(node)
        self.active.push(obj)


    def visit_ExceptHandler(self, node):
        self.iter_field(node.type)
        name = self.active.pop()
        start = self.active.size()
        self.iter_field(node.body)
        end = self.active.size()
        body = JavaStatements()
        self.fill(body, end - start)
        obj = JavaExceptHandler(name, body)
        obj.set_metadata(node)
        self.active.push(obj)


    def visit_While(self, node):
        self.iter_field(node.test)
        test = self.active.pop()
        start = self.active.size()
        self.iter_field(node.body)
        end = self.active.size()
        body = JavaStatements()
        self.fill(body, end - start)
        obj = JavaWhile(test, body)
        obj.set_metadata(node)
        self.active.push(obj)


    def visit_Break(self, node):
        self.active.push(JavaBreak())


    def visit_comprehension(self, node):
        if DEBUG:
            print("-----------start node  %s -----------" % node.__class__.__name__)
            print(ast.dump(node))
        self.iter_field(node.target)
        target = self.active.pop()
        self.iter_field(node.iter)
        iterator = self.active.pop()

        body = JavaStatements()
        if node.ifs:
            start = self.active.size()
            for if_ in node.ifs:
                self.iter_field(if_)
            end = self.active.size()
            self.fill(body, end - start)

        obj = JavaComprehension(target, iterator, body)
        # obj.set_metadata(node)
        self.active.push(obj)
