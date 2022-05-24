#!/usr/bin/env python3

import string
import sys

RESERVED_WORDS = {
    "program", "if", "switchcase", "not", "function", "input", "declare", "else", "forcase", "and", "procedure",
    "print", "while", "incase", "or", "call", "case", "return", "default", "in", "inout"
}

REL_OPS = {"=", "<=", ">=", ">", "<", "<>"}

ADD_OPS = {"+", "-"}

MUL_OPS = {"*", "/"}


class AsmGenerator:
    def __init__(self, code_parser):
        self.parser = code_parser
        self.statements = []

    def compile_block(self, block_name):
        inside_block = False
        for q in self.parser.quads:
            if q.x == block_name and q.op == "begin_block":
                inside_block = True
            if inside_block:
                self.statements += self.quad_to_asm(q)
            if q.x == block_name and q.op == "end_block":
                break

    def current_scope(self):
        return len(self.parser.st.scopes) - 1

    def gnvlcode(self, var):  # t0 = &var
        ent = self.parser.st.find_entity(name=var, categories=("variables", "tmp_variables", "parameters"))
        offset_repeat = self.current_scope() - ent["scope"]
        return ["lw t0,-4(sp)"] + ["lw t0,-4(t0)"] * offset_repeat + ["addi t0,t0,-%d" % ent["offset"]]

    def loadvr(self, var, tr):  # tr = var
        try:
            const = int(var)
            return [f"li {tr},{const}"]
        except ValueError:
            return self.sl_vr(var, tr, store=False)

    def storerv(self, tr, var):  # var = tr
        return self.sl_vr(var, tr, store=True)

    def sl_vr(self, var, tr, store=False):  # if store=True then storerv else loadvr
        ent = self.parser.st.find_entity(name=var, categories=("variables", "parameters", "tmp_variables"))
        stmt = "sw" if store else "lw"

        if ent["offset"] == 0:  # global var (declared in main)
            return ["%s %s,-%d(gp)" % (stmt, tr, ent["offset"])]
        elif self.current_scope() - ent["scope"]:  # variable is declared in current func
            if "mode" in ent and ent["mode"] == "inout":
                return ["lw t0,-%d(sp)" % ent["offset"], "%s tr,(t0)" % stmt]
            return ["%s %s,-%d(sp)" % (stmt, tr, ent["offset"])]
        else:  # variable declared in ancestor
            asm = self.gnvlcode(var)
            if "mode" in ent and ent["mode"] == "inout":
                asm += ["lw t0,(t0)"]
            return asm + ["%s tr,(t0)" % stmt]

    def quad_to_asm(self, q):
        asm = [q.label + ":"]
        framelength = self.parser.st.scopes[-1]["offset"]

        if q.op == "begin_block":
            if q.z == "main":
                asm += ["Lmain:", "addi sp,sp,%d" % framelength, "mv gp,sp"]
            else:
                asm += ["add sp,sp,%d" % framelength] + ["sw ra,(sp)"]
            return asm
        elif q.op == "end_block":
            return asm
        elif q.op == ":=":
            return asm + self.loadvr(q.x, "t1") + self.storerv("t1", q.z)
        elif q.op in ("+", "-", "*", "/"):
            stmt = {"+": "add", "-": "sub", "*": "mul", "/": "div"}[q.op]
            return asm + self.loadvr(q.x, "t1") + self.loadvr(q.y, "t2") + \
                   ["%s, t1, t1, t2" % stmt] + self.storerv("t1", q.z)
        elif q.op == "jump":
            return asm + ["j %s" % q.z]
        elif q.op in ("=", "<>", ">", "<", ">=", "<="):
            stmt = {"=": "beq", "<>": "bne", ">": "bgt", "<": "blt", ">=": "bge", "<=": "ble"}[q.op]
            return asm + self.loadvr(q.x, "t1") + self.loadvr(q.y, "t2") + ["%s t1,t2,%s" % (stmt, q.label)]
        elif q.op == "retv":
            return asm + self.loadvr(q.x, "t1") + ["lw t0,-8(sp)", "sw t1,(t0)"]
        elif q.op == "call":
            ent = self.parser.st.find_entity(q.x, categories=("functions", "procedures",))
            if ent["scope"] == self.current_scope():
                asm = ["lw t0,-4(sp)", "sw t0,-4(fp)"] + asm
            else:
                asm = ["sw sp,-4(fp)"] + asm
            return asm + ["addi sp,sp,%d" % framelength, "jal %s" % q.x, "add sp,sp,-%d" % framelength]
        elif q.op == "out":
            return asm + self.loadvr(q.x, "t1") + ["mv a0,t1", "li a7,1", "ecall"] + \
                   ["la a0,str_nl", "li a7,4", "ecall"]
        elif q.op == "inp":
            return asm + ["li a7,5", "ecall"] + self.storerv("a0", q.x)
        elif q.op == "par":
            ent = self.parser.st.find_entity(q.x, categories=("parameters", "tmp_variables", "variables"))
            if q.y == "REF":
                if self.current_scope() == ent["scope"]:  # variable is declared in current func
                    asm += ["addi t0,sp,-%d" % ent["offset"]]
                else:
                    self.gnvlcode(q.x)
            if q.y in ("REF", "CV"):
                try:
                    const = int(q.x)
                    return asm + [f"sw t0,{const}"]
                except ValueError:
                    return asm + self.loadvr(q.x, "t0") + ["sw t0,(-%d)(fp)" % (12 + ent["offset"])]
            if q.y == "RET":
                return asm + ["addi t0,sp,-%d" % ent["offset"], "sw t0,-8(fp)"]
        elif q.op == "halt":
            return asm + ["li a0,0", "li a7,93", "ecall"]

        raise Exception("invalid quad operator: %s" % q.op)

    def gen_asm_equivalent(self):
        return "\n".join(x if x.endswith(":") else "\t" + x for x in
                         [".data", "str_nl: .asciiz \"\\n\"", ".text",
                          ".global __start", "__start:", "j Lmain"] + self.statements)


class SymbolTable:
    def __init__(self, code_parser):
        self.parser = code_parser
        self.scopes = []

    def assert_declared(self, name, categories):
        if self.parser.st.find_entity(name, categories) is None:
            raise CompilationError("Symbol '%s' does not belong to %s." % (name, " or ".join(categories)),
                                   self.parser.tokens[self.parser.token_idx].cursor, self.parser.lines)

    def create_scope(self, name=""):
        self.scopes.append({"name": name, "offset": 12, "entities": {
            "variables": {}, "tmp_variables": {}, "functions": {}, "procedures": {}, "parameters": {}}})

    def add_new_entity(self, category, name, entity):
        if self.parser.st.find_entity(name, max_depth=1):
            raise CompilationError("Symbol '%s' is already declared in the same scope." % name,
                                   self.parser.tokens[self.parser.token_idx].cursor, self.parser.lines)

        if category in ("variables", "parameters", "tmp_variables"):
            entity["offset"] = self.scopes[-1]["offset"]
            self.scopes[-1]["offset"] += 4

        entity["scope"] = len(self.scopes) - 1
        self.scopes[-1]["entities"][category][name] = entity

    def find_entity(self, name, categories=("variables", "functions", "parameters", "procedures", "tmp_variables"),
                    max_depth=None):
        for scope in self.scopes[::-1][:max_depth if max_depth is not None else len(self.scopes)]:
            for cat in categories:
                if name in scope["entities"][cat]:
                    return scope["entities"][cat][name]
        return None


class Parser:
    def __init__(self, lexer):
        self.lines = lexer.lines
        self.tokens = []
        self.token_idx = 0
        self.quads = []
        self.temp_seq = 0
        self.st = SymbolTable(self)
        self.asm_generator = AsmGenerator(self)

        while True:
            u = lexer.next()
            if u is None:
                break
            self.tokens.append(Token(lexer, u, FilePos(lexer.pos.ln, lexer.pos.cl - len(u))))

    def next(self, peek=False):
        try:
            t = self.tokens[self.token_idx]
            self.token_idx = self.token_idx if peek else self.token_idx + 1
            return t
        except IndexError:
            raise CompilationError("Program should end with a dot (.)")

    def peek(self):
        return self.next(peek=True)

    def next_quad_label(self):
        return "L_" + str(len(self.quads) + 1)

    def new_temp(self):
        self.temp_seq += 1
        name = f"T_{self.temp_seq}"
        self.st.add_new_entity(category="tmp_variables", name=name, entity={})
        return name

    def new_quad(self, op="", x="", y="", z=""):
        self.quads.append(Quad(self.next_quad_label(), op, x, y, z))
        return self.quads[-1]

    @staticmethod
    def backpatch(quads, z):
        for q in quads:
            if q.z == "":
                q.z = z

    def parse_program(self):
        self.next().assert_value_is("program")
        ident = self.next().assert_is_identifier()
        self.st.create_scope(name=ident.value)
        self.parse_block(ident.value, is_main=True)
        self.st.scopes.pop()
        self.next().assert_value_is(".")

    def parse_block(self, name, is_main=False):
        self.next().assert_value_is("{")
        self.parse_declarations()
        self.parse_subprograms()
        self.new_quad("begin_block", name, z="main" if is_main else "")
        self.parse_block_statements()
        if is_main:
            self.new_quad("halt")
        self.new_quad("end_block", name)
        self.next().assert_value_is("}")
        self.asm_generator.compile_block(name)

    def parse_declarations(self):
        while True:
            if not self.peek().value_is("declare"):
                return
            self.next()
            self.parse_varlist()
            self.next().assert_value_is(";")

    def parse_varlist(self):
        if not self.peek().is_identifier():
            return

        while True:
            ident = self.next().assert_is_identifier()
            self.st.add_new_entity(category="variables", name=ident.value, entity={})

            if not self.peek().value_is(","):
                return
            self.next()

    def parse_subprograms(self):
        while True:
            if not self.peek().value_in(("function", "procedure")):
                return
            self.parse_subprogram()

    def parse_subprogram(self):
        typ = self.next().assert_value_in(("function", "procedure"))
        ident = self.next().assert_is_identifier()
        self.next().assert_value_is("(")
        params = self.parse_formalparlist()
        self.next().assert_value_is(")")
        entity = {"start_quad": self.next_quad_label(), "signature": [p["mode"] for p in params]}
        self.st.add_new_entity(category=typ.value + "s", name=ident.value, entity=entity)
        self.st.create_scope(ident.value)
        for p in params:
            self.st.add_new_entity(category="parameters", name=p["name"], entity={"mode": p["mode"]})
        self.parse_block(ident.value)
        entity["framelength"] = self.st.scopes[-1]["offset"]
        self.st.scopes.pop()

    def parse_formalparlist(self):
        params = []
        if not self.peek().value_in(("in", "inout")):
            return params

        while True:
            par_mode = self.next().assert_value_in(("in", "inout"))
            ident = self.next().assert_is_identifier()
            params.append({"mode": par_mode.value, "name": ident.value})

            if not self.peek().value_is(","):
                return params
            self.next()

    def parse_statements(self):
        if self.peek().value_is("{"):
            self.next()
            self.parse_block_statements()
            self.next().assert_value_is("}")
        else:
            self.parse_statement()
            self.next().assert_value_is(";")

    def parse_block_statements(self):
        while True:
            self.parse_statement()
            if not self.peek().value_is(";"):
                return
            self.next()

    def parse_statement(self):
        t = self.peek()

        if t.is_identifier():
            self.parse_assign()
        elif t.value_is("if"):
            self.parse_if()
        elif t.value_is("while"):
            self.parse_while()
        elif t.value_is("switchcase"):
            self.parse_switchcase()
        elif t.value_is("forcase"):
            self.parse_forcase()
        elif t.value_is("incase"):
            self.parse_incase()
        elif t.value_is("call"):
            self.parse_call()
        elif t.value_is("return"):
            self.parse_return()
        elif t.value_is("input"):
            self.parse_input()
        elif t.value_is("print"):
            self.parse_print()
        else:
            return

    def parse_assign(self):
        ident = self.next().assert_is_identifier()
        self.st.assert_declared(ident.value, categories=["variables", "parameters"])
        self.next().assert_value_is(":=")
        it = self.parse_expression()
        self.new_quad(":=", it, z=ident.value)

    def parse_if(self):
        self.next().assert_value_is("if")
        self.next().assert_value_is("(")
        tf = self.parse_condition()
        self.next().assert_value_is(")")
        self.backpatch(tf.t, self.next_quad_label())
        self.parse_statements()
        j = self.new_quad("jump")
        self.backpatch(tf.f, self.next_quad_label())
        self.parse_else()
        self.backpatch([j], self.next_quad_label())

    def parse_else(self):
        if self.peek().value_is("else"):
            self.next()
            self.parse_statements()

    def parse_while(self):
        cond_quad = self.next_quad_label()
        self.next().assert_value_is("while")
        self.next().assert_value_is("(")
        tf = self.parse_condition()
        self.next().assert_value_is(")")
        self.backpatch(tf.t, self.next_quad_label())
        self.parse_statements()
        self.new_quad("jump", z=cond_quad)
        self.backpatch(tf.f, self.next_quad_label())

    def parse_switchcase(self):
        self.next().assert_value_is("switchcase")
        jump_out = []

        while True:
            if not self.peek().value_is("case"):
                break

            self.next()
            self.next().assert_value_is("(")
            tf = self.parse_condition()
            self.next().assert_value_is(")")
            self.backpatch(tf.t, self.next_quad_label())
            self.parse_statements()
            jump_out.append(self.new_quad("jump"))
            self.backpatch(tf.f, self.next_quad_label())

        self.next().assert_value_is("default")
        self.parse_statements()

        self.backpatch(jump_out, self.next_quad_label())

    def parse_forcase(self):
        self.next().assert_value_is("forcase")
        first_quad = self.next_quad_label()

        while True:
            if not self.peek().value_is("case"):
                break

            self.next()
            self.next().assert_value_is("(")
            tf = self.parse_condition()
            self.next().assert_value_is(")")
            self.backpatch(tf.t, self.next_quad_label())
            self.parse_statements()
            self.new_quad("jump", z=first_quad)
            self.backpatch(tf.f, self.next_quad_label())

        self.next().assert_value_is("default")
        self.parse_statements()

    def parse_incase(self):
        self.next().assert_value_is("incase")
        first_quad = self.next_quad_label()
        flag = self.new_quad(":=", "0", z=self.new_temp())

        while True:
            if not self.peek().value_is("case"):
                break

            self.next()
            self.next().assert_value_is("(")
            tf = self.parse_condition()
            self.backpatch(tf.t, self.next_quad_label())
            self.next().assert_value_is(")")
            self.parse_statements()
            self.new_quad(":=", "1", z=flag.z)
            self.backpatch(tf.f, self.next_quad_label())

        self.new_quad("=", flag.z, "1", first_quad)

    def parse_call(self):
        self.next().assert_value_is("call")
        ident = self.next().assert_is_identifier()
        self.st.assert_declared(ident.value, categories=["procedures"])
        self.next().assert_value_is("(")
        self.parse_actualparlist()
        self.next().assert_value_is(")")
        self.new_quad("call", ident.value)

    def parse_return(self):
        self.next().assert_value_is("return")
        self.next().assert_value_is("(")
        it = self.parse_expression()
        self.next().assert_value_is(")")
        self.new_quad("retv", it)

    def parse_input(self):
        self.next().assert_value_is("input")
        self.next().assert_value_is("(")
        ident = self.next().assert_is_identifier()
        self.next().assert_value_is(")")
        self.new_quad("inp", ident.value)

    def parse_print(self):
        self.next().assert_value_is("print")
        self.next().assert_value_is("(")
        it = self.parse_expression()
        self.next().assert_value_is(")")
        self.new_quad("out", it)

    def parse_actualparlist(self):
        if not self.peek().value_in(("in", "inout")):
            return

        while True:
            self.parse_actualparitem()
            if not self.peek().value_is(","):
                return
            self.next()

    def parse_actualparitem(self):
        par_typ = self.next().assert_value_in(("in", "inout"))

        if par_typ.value == "inout":
            it = self.next().assert_is_identifier().value
        else:
            it = self.parse_expression()

        self.new_quad("par", it, "CV" if par_typ.value == "in" else "REF")

    def parse_condition(self):
        tf = TrueFalse()

        while True:
            tf.append(self.parse_boolterm())
            if not self.peek().value_is("or"):
                tf.append(TrueFalse(f=[self.new_quad("jump")]))
                return tf

            self.backpatch(tf.f, self.next_quad_label())
            self.next()

    def parse_boolterm(self):
        tf = TrueFalse()

        while True:
            bf = self.parse_boolfactor()
            tf.append(bf)
            if not self.peek().value_is("and"):
                return tf

            self.next()
            tf.append(TrueFalse(f=[self.new_quad("jump")]))
            self.backpatch(bf.t, self.next_quad_label())

    def parse_boolfactor(self):
        p = self.peek()

        if p.value_is("not"):
            self.next().assert_value_is("not")
            self.next().assert_value_is("[")
            tf = self.parse_condition()
            self.next().assert_value_is("]")
            tf.f, tf.t = tf.t, tf.f
            return tf
        elif p.value_is("["):
            self.next().assert_value_is("[")
            tf = self.parse_condition()
            self.next().assert_value_is("]")
            return tf
        it1 = self.parse_expression()
        relop = self.next().assert_value_in(REL_OPS)
        it2 = self.parse_expression()
        return TrueFalse(t=[self.new_quad(relop.value, it1, it2)])

    def parse_expression(self):
        opsign_tk = self.parse_opsign()
        exp = self.parse_term()

        if opsign_tk and opsign_tk.value == "-":
            exp = self.new_quad("-", "0", exp, self.new_temp()).z

        while self.peek().value_in(ADD_OPS):
            addop = self.next().value
            term = self.parse_term()
            exp = self.new_quad(addop, exp, term, self.new_temp()).z

        return exp

    def parse_term(self):
        term = self.parse_factor()
        while self.peek().value_in(MUL_OPS):
            mulop = self.next().value
            fac = self.parse_factor()
            term = self.new_quad(mulop, term, fac, self.new_temp()).z

        return term

    def parse_factor(self):
        p = self.peek()

        if p.value_is("("):
            self.next()
            fac = self.parse_expression()
            self.next().assert_value_is(")")
        elif p.value.isdigit():
            fac = self.next().value
        elif p.value.isalnum():
            fac = self.next().assert_is_identifier().value
            if self.peek().value_is("("):
                res = self.parse_idtail()
                self.new_quad("call", fac)
                self.st.assert_declared(fac, categories=["functions"])
                fac = res
            else:
                self.st.assert_declared(fac, categories=["variables", "parameters"])
        else:
            raise CompilationError("Expected integer, expression or function call.", p.cursor, self.lines)

        return fac

    def parse_idtail(self):
        self.next().assert_value_is("(")
        self.parse_actualparlist()
        self.next().assert_value_is(")")
        return self.new_quad("par", self.new_temp(), "RET").x

    def parse_opsign(self):
        if self.peek().value_in(ADD_OPS):
            return self.next()

    def gen_c_equivalent(self):
        variables = set()
        for q in self.quads:
            if q.op == "begin_block" and q.label != "L_1":
                raise Exception("Cannot generate c code for programs that include functions and procs!")

            [variables.add(v) for v in (q.x, q.y, q.z) if
             v.isidentifier() and v not in ("CV", "REF", "RET") and not v.startswith("L_")]

        declarations = "int " + ", ".join(variables) + ";\n"
        body = "".join([f"// {str(q)}\n{q.label}:\t {q.to_c()};\n" for q in self.quads])
        return f"#include <stdlib.h>\n#include <stdio.h>\nint main() {{\n{declarations + body}\nreturn 0;\n}}"


class Quad:
    def __init__(self, label="", op="", x="", y="", z=""):
        self.label = label
        self.op = op
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return f"{self.label}:\t{self.op}, {self.x}, {self.y}, {self.z}"

    def to_c(self):
        if self.op in ("+", "-", "*", "/"):
            return f"{self.z} = {self.x} {self.op} {self.y}"
        if self.op in ("<", "=", ">", "<=", ">=", "<>"):
            op = {"<>": "!=", "=": "=="}.get(self.op, self.op)
            return f"if ({self.x} {op} {self.y}) goto {self.z}"
        if self.op == "jump":
            return f"goto {self.z}"
        if self.op == ":=":
            return f"{self.z} = {self.x}"
        if self.op == "out":
            return f"printf(\"%d\\n\", {self.x})"
        if self.op == "inp":
            return f"scanf(\"%d\", &{self.x})"
        if self.op in ("begin_block", "halt", "end_block"):
            return ""
        raise Exception("unknown c equivalent for %s" % (str(self)))


class TrueFalse:
    def __init__(self, t=None, f=None):
        self.t = t if t is not None else []
        self.f = f if f is not None else []

    def append(self, tf):
        self.t += tf.t
        self.f += tf.f


class Lex:
    def __init__(self, src):
        self.lines = src.split("\n")
        self.pos = FilePos()

    def next_char(self, peek=False):
        if self.pos.ln >= len(self.lines):
            return None
        elif self.pos.cl == len(self.lines[self.pos.ln]):
            if not peek:
                self.pos.ln += 1
                self.pos.cl = 0
            return "\n"

        c = self.lines[self.pos.ln][self.pos.cl]
        if not peek:
            self.pos.cl += 1
        return c

    def next(self):
        c = self.next_char(peek=True)

        if c is None:
            return None
        elif c in string.ascii_letters:
            return self.parse_var()
        elif c in string.digits:
            return self.parse_const()
        elif c in "+-*/=;,[](){}.":
            return self.next_char()
        elif c == "<":
            u = self.next_char()
            if self.next_char(peek=True) in ("=", ">"):
                u += self.next_char()
            return u
        elif c == ">":
            u = self.next_char()
            if self.next_char(peek=True) == "=":
                u += self.next_char()
            return u
        elif c == ":":
            u = self.next_char()
            if self.next_char(peek=True) != "=":
                raise CompilationError("Invalid assignment operator", self.pos, self.lines)
            return u + self.next_char()
        elif c == "#":
            self.next_char()
            c = self.next_char()
            while c not in ("#", None):
                c = self.next_char()
            if c is None:
                raise CompilationError("Unterminated comment at the end of the program.")
            return self.next()
        elif c in (" ", "\t", "\r\n", "\n"):
            self.next_char()
            return self.next()
        else:
            raise CompilationError("Invalid character %s" % repr(c), self.pos, self.lines)

    def parse_var(self):
        u = self.next_char()
        while True:
            if not self.next_char(peek=True).isalnum():
                return u

            u += self.next_char()
            if len(u) > 30:
                raise CompilationError("Variable name cannot be more than 30 chars.", self.pos, self.lines)

    def parse_const(self):
        u = self.next_char()
        while True:
            p = self.next_char(peek=True)
            if p not in string.digits:
                if p in string.ascii_letters:
                    raise CompilationError("Variable name cannot start with a number.", self.pos, self.lines)
                if int(u) > 2 ** 32 - 1:
                    raise CompilationError("Constant max value is 2^32-1 (%d)." % (2 ** 32 - 1), self.pos, self.lines)
                return u
            u += self.next_char()


class Token:
    def __init__(self, lexer, value, cursor):
        self.lex = lexer
        self.value = value
        self.cursor = cursor

    def value_is(self, value):
        return self.value == value

    def value_in(self, values):
        return self.value in values

    def is_identifier(self):
        return self.value.isalnum() and self.value not in RESERVED_WORDS

    def assert_value_is(self, value):
        if not self.value_is(value):
            raise CompilationError("Unexpected: '%s', closest expected value: '%s'." % (self.value, value),
                                   self.cursor, self.lex.lines)
        return self

    def assert_value_in(self, values):
        if not self.value_in(values):
            raise CompilationError("Unexpected: '%s', expected one of: '%s'." % (self.value, values),
                                   self.cursor, self.lex.lines)
        return self

    def assert_is_identifier(self):
        if not self.value.isalnum():
            raise CompilationError("Expected an identifier, got: '%s'." % self.value, self.cursor, self.lex.lines)
        if self.value in RESERVED_WORDS:
            raise CompilationError("Cannot use '%s' for a variable name." % self.value, self.cursor, self.lex.lines)
        return self


class FilePos:
    def __init__(self, ln=0, cl=0):
        self.ln, self.cl = ln, cl


class CompilationError(Exception):
    def __init__(self, msg, pos=None, lines=None):
        self.msg = msg
        self.pos = pos
        self.lines = lines

    def __str__(self):
        s = f"ERROR: {self.msg}"

        if self.pos is not None:
            s += f"\n({self.pos.ln + 1}:{self.pos.cl + 1})"

        if self.lines is not None:
            line_preview = self.lines[self.pos.ln][max(0, self.pos.cl - 10):self.pos.cl + 10]
            s += f"\t near: `...{line_preview}...`"

        return s


if __name__ == "__main__":
    try:
        filename = sys.argv[1]
        gen_c = len(sys.argv) > 2 and sys.argv[2] == "--gen-c"

        parser = Parser(Lex(open(filename, "r").read()))
        parser.parse_program()

        if gen_c:
            with open(filename + ".c", "w") as cf:
                cf.write(parser.gen_c_equivalent())

        with open(filename + ".asm", "w") as af:
            af.write(parser.asm_generator.gen_asm_equivalent())
    except CompilationError as e:
        print(e)
        sys.exit(2)
    except Exception as e:
        raise e
