import sys
# import jupyter_aws as jaws
# from jupyter_aws.known_secret import KnownSecret, SecretId
# from foundrysmith.error_report import ErrorReport
import os
import re
import json
from lark import Lark, Transformer
from lark.lexer import Lexer, Token
from io import StringIO, IOBase
import sys
import re
from typing import List, Union
import sys

class ErrorReport:
    def __init__(self):
        self.error_count = 0

    def error(self, msg):
        print(msg, file=sys.stderr)
        self.error_count += 1

    def exit_on_error(self):
        if self.error_count>0:
            print("Exit on error", file=sys.stderr)
            sys.exit(1)

class SecretId:
    def __init__(self, name):
        self.name = name

    @classmethod
    def by_value(cls, name):
        return SecretId(name)

class KnownSecret:
    def __init__(self):
        pass
    def get_secret(self, id):
        return { "name": id.name, "sonartoken": f"!!!sonartoken-{id.name}!!!" }

class Arglist:
    def __init__(self, args):
        self.args = args

    def shift(self):
        arg = self.args[0]
        self.args = self.args[1:]
        return arg

errors = ErrorReport()

def usage():
    """- Shows usage information for fill-template.py"""
    print("Usage: fill-template.py [-D <VARNAME>=<value>] <templatefile>")
    sys.exit(1)


def replace_variable(body, span, varvalue):
    """- Global string replacement in the body of a document
    Args:
        body :str: The document being changed
        span :str: The text that was detected as replaceable
        varvalue :str: Replacement for the span
    """
    #print(f"replace_variable(body..., {span}, {varvalue})")
    if varvalue is None:
        varvalue = "NODATA"
    body = body.replace(span, varvalue)
    #print(body)
    return body

def get_secret(varname : str) -> str:
    """- Fetches a well known secret value from its SecretId
    Args:
        varname :str: The name of the secret, which must match a known SecretId value
    Returns:
        :str: the value of the secret
    """

    secrets = KnownSecret()
    varvalue = None
    try:
        secretid = SecretId.by_value(varname)
        varvalue = secrets.get_secret(secretid)
        if varvalue is None:
            raise ValueError(f"invalid secret {varname}")
    except AttributeError:
        errors.error(f"Value error: Unable to get secret '{varname}'")

    #print("get_secret", varname, "->", varvalue)
    return varvalue


settings = None
def get_setting(varname : str) -> str:
    """- Returns an entry from a shell script 'setting.sh' in your local directory

    The file 'setting.sh' must contain shell variable definitions in the format:
        VARNAME="<value>"
    Any lines that do not have that format are ignored.

    Args:
        varname :str: The name of the setting to fetch
    Returns:
        :str: the value of the shell variable (ie the dequoted string)
    """
    global settings
    if settings is None:
        with open("setting.sh", "rt") as f:
            settings = {}
            for line in f.readlines():
                m = re.match(r'^ *([A-Za-z][A-Za-z0-9]*)="(.*)"$', line)
                if m:
                    var = m.group(1)
                    val = m.group(2)
                    print(f"Setting {var}={val}")
                    settings[var] = val
    return settings[varname]


def find_replace_variables(body : str) -> str:
    """- Interpolates variables in the body of a document

    Variables have the form '@<type>:<varname>[.<property>]@'.  The supported
    values for <type> are:
       - secret: fetches a secret from keyring or AWS SecretsManager depending on environment
       - env: fetches an environment variable
       - setting.sh: fetches a shell variable from 'setting.sh' in local directory

    The <varname> part must match a well-known SecretID value to use the 'secret' type.   For
    other types the <varname> will match the shell variable name.

    Args:
        body :str: The document body to be interpolated.
    """
    while True:
        m = re.search(r"@([a-zA-Z_\.-]+):([a-zA-Z_\.-]+)@", body)
        if m:
            span = m.group(0)
            vartype = m.group(1)
            varname = m.group(2)
            #print(f"find_replace_variables: {vartype} {varname}")
            if vartype == "secret":
                varname, varprop = varname.split(".")
                varvalue = get_secret(varname)[varprop]
            elif vartype == "env":
                varvalue = os.environ.get(varname)
                if varvalue is None:
                    errors.error(f"Value error: Unable to get env '{varname}'")
            elif vartype == "setting.sh":
                varvalue = get_setting(varname)
            else:
                errors.error(f"Unknown variable type: '{vartype}'")
                varvalue = None
            body = replace_variable(body, span, varvalue)
        else:
            break
    return body

class Fpos:
    """Windowed view of an input stream"""
    def __init__(self, data : Union[str, IOBase, List[str]]):
        """ - Provides a windowed view of an input stream
        Args:
        data :Union[str, IOBase, List[str]]: A file path or derivative class of IOBase to read from, or a list of lines
        """
        if type(data) is str:
            with open(data, "rt") as f:
                lines = f.readlines()
        elif isinstance(data, IOBase):
            lines = data.readlines()
        elif type(data) is list:
            lines = data
        else:
            raise ValueError("Invalid data")
        self.lines = lines
        self.cpos = 0
        self.rpos = 0

    @property
    def v(self):
        """- Returns the current row and column view of the stream"""
        #print(self.rpos,self.cpos,self.lines[self.rpos][self.cpos:])
        return self.lines[self.rpos][self.cpos:]

    @property
    def eof(self):
        """- Returns true if the row is past the end of the stream"""
        if self.rpos >= len(self.lines):
            return True
        return False

    def skip(self, n):
        """- Moves the cursor forward
        Args:
            n :int: count of characters to move forward.  If the column moves
            past the end of line the row will be advanced and the column is set
            to 0
        """
        self.cpos += n
        if self.cpos >= len(self.lines[self.rpos]):
            self.cpos = 0
            self.rpos += 1

class PreprocessorLexer(Lexer):
    """Tokenizes an input file returning TEXT tokens for unrecognized text, and preprocessor
    tokens for C preprocessor instructions.  Whitespace is ignored by the lexical analyzer except
    that it resets the state to rules0"""
    rules0 = {
        "INCLUDE": r"^#[ ]*include",
        "DEFINE": r"^#[ ]*define",
        "IFDEF": r"^#[ ]*ifdef",
        "IF": r"^#[ ]*if",
        "ELSE": r"^#[ ]*else",
        "ENDIF": r"^#[ ]*endif",
    }
    rules0priority = [
        'INCLUDE', 'IFDEF', 'IF', 'ENDIF', 'ELSE', 'DEFINE'
    ]
    rules1 = {
        "SPACE": r"[\t ]+",
        "SYMBOL": r"[A-Za-z_][A-Za-z0-9_]*",
        "COMP": r"(==|<=|>=|<|>)",
        "ASSIGN": r"=",
        "UNARY": r"!",
        "DEFINED": r"defined",
        "(": r"\(",
        ")": r"\)",
        "STRING": r'"[^"]*"',
        "EOL": r"\n",
    }
    rules1priority = [
        'SPACE', 'SYMBOL', 'COMP', 'UNARY', 'ASSIGN', 'DEFINED', '(', ')', 'STRING', 'EOL'
    ]

    def __init__(self, lexer_conf=None):
        """- Construct PreprocessorLexer"""
        pass

    def next_token(self, fp):
        """- Fetch the next token"""
        if fp.eof: return None
        if fp.cpos == 0:
            for r in self.rules0priority:
                m = re.match(self.rules0[r], fp.v)
                #print(m, self.rules0[r], fp.v)
                if m:
                    token = Token(r, m.group(0), 0, fp.rpos, fp.cpos)
                    fp.skip(len(token.value))
                    return token
            token = Token("TEXT", fp.v, 0, fp.rpos, fp.cpos)
            fp.skip(len(token.value))
            return token
        else:
            for r in self.rules1priority:
                m = re.match(self.rules1[r], fp.v)
                if m:
                    token = Token(r, m.group(0), 0, fp.rpos, fp.cpos)
                    fp.skip(len(token.value))
                    return token
            raise TypeError(f"Invalid token at {fp.v}")

    def lex(self, fp):
        """- Generates tokens until EOF.  Whitespace tokens are skipped.
        Args:
          fp :Fpos: The input stream to read from
        """
        tok = self.next_token(fp)
        #print("lex",tok)
        while tok:
            if not (tok.type == 'SPACE' or tok.type == 'EOL'):
                yield tok
            tok = self.next_token(fp)
            #print("lex",tok)


class Instruction:
    def __init__(self, opcode, arg1=None, arg2=None):
        self.op = [opcode, arg1, arg2]

    def __repr__(self) -> str:
        opcode = self.opcode
        arg1 = self.arg1
        arg2 = self.arg2
        if arg1:
            if arg2:
                return f"{opcode}({arg1},{arg2})"
            else:
                return f"{opcode}({arg1})"
        else:
            return f"{opcode}"


    @property
    def opcode(self):
        return self.op[0]

    @property
    def arg1(self):
        return self.op[1]

    @property
    def arg2(self):
        return self.op[2]

class PreprocessorVM:
    def __init__(self, env=None):
        if env is None:
            env = {}
        self.stack = []
        self.vars = env
        self.progmem = [ Instruction('LABEL', 'main') ]
        self.pc = 0
        self.seg_count = 0
        self.output = []
        self.running = False
        self.labels = {}
        self.scan_labels()

    def scan_labels(self):
        for pc,i in enumerate(self.progmem):
            if i.opcode == 'LABEL':
                self.labels[i.arg1] = pc

    def prog(self, instr):
        self.progmem.extend(instr)
        self.scan_labels()

    def gensym(self):
        self.seg_count += 1
        return f"SEG_{self.seg_count:03d}"

    def push(self, v):
        self.stack.append(v)

    def pop(self):
        v = self.stack[-1]
        del self.stack[-1]
        return v

    def interpolate(self, body):
        for v in self.vars:
            body = body.replace(v, self.vars[v])
        return body

    def execute1(self):
        if not self.running: return
        pc = self.pc
        instr = self.progmem[pc]
        #print(pc, instr)
        opcode = instr.opcode
        arg1 = instr.arg1
        arg2 = instr.arg2
        pc += 1
        self.pc = pc
        if opcode == 'EMIT':
            self.output.append(self.interpolate(arg1))
        elif opcode == 'GET':
            self.push(self.vars[arg1])
        elif opcode == 'CONST':
            self.push(arg1)
        elif opcode == 'EVAL2':
            cond = arg1
            a = self.pop()
            b = self.pop()
            if cond == '==':
                v = (a == b)
            elif cond == '<=':
                v = (a <= b)
            elif cond == '>=':
                v = (a >= b)
            elif cond == '<':
                v = (a < b)
            elif cond == '>':
                v = (a > b)
            elif cond == '!=':
                v = (a != b)
            self.push(v)
        elif opcode == 'EVAL1':
            cond = arg1
            a = self.pop()
            if cond == '!':
                v = not a
            elif cond == 'defined':
                v = (a in self.vars)
            self.push(v)
        elif opcode == 'JMPIF':
            cond = self.pop()
            sym = arg1
            if cond:
                self.pc = self.labels[lbl]
        elif opcode == 'JMP':
            lbl = arg1
            self.pc = self.labels[lbl]
        elif opcode == 'SET':
            var = arg1
            val = self.pop()
            self.vars[var] = val
        elif opcode == 'INCLUDE':
            raise NotImplementedError("Not implemented INCLUDE")
        elif opcode == 'HALT':
            self.running = False
        elif opcode == 'EXISTS':
            sym = arg1
            self.push(sym in self.vars)
        elif opcode == 'LABEL':
            lbl = arg1
            #print(lbl)
        elif opcode == 'FATAL':
            msg = arg1
            print(msg, file=sys.stderr)
            sys.exit(1)

    def execute(self):
        self.pc = self.labels['main']
        self.running = True
        while (self.running):
            try:
                self.execute1()
            except Exception as e:
                print(self.pc, str(e))
                raise e


# Syntax definition for the preprocessor
preprocessor_bnf = r"""
start: block

block: anyitem*

anyitem: body
    | condbody
    | include
    | define

?include: INCLUDE STRING -> include

define: DEFINE SYMBOL expr? -> setsymbol

condbody: IF bexpr block ENDIF -> condbody
    | IF bexpr block ELSE block ENDIF -> condbody
    | IFDEF SYMBOL block ENDIF -> condbody2
    | IFDEF SYMBOL block ELSE block ENDIF -> condbody2

body: TEXT+

bexpr: expr COMP expr -> expr2
    | UNARY bexpr -> expr1
    | DEFINED "(" SYMBOL ")" -> expr1

expr: SYMBOL -> eval1
    | STRING -> eval1

%declare TEXT IF IFDEF ELSE ENDIF INCLUDE DEFINE SYMBOL ASSIGN STRING COMP UNARY DEFINED
"""



# Utility functions
def unwrap_str(s):
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


# Parser tree transformer to output file (as a list of lines)
class ParsePreprocessor(Transformer):
    def __init__(self, vm : PreprocessorVM):
        self.vm = vm

    def start(self, v):
        block = v[0]
        result = block + [
            Instruction('HALT')
        ]
        return result

    def block(self, v):
        result = []
        for i in v:
            result.extend(i)
        #print(f"node start {result}", file=sys.stderr)
        return result

    def anyitem(self, v):
        #print(f"node anyitem {v[0]}", file=sys.stderr)
        return v[0]

    def setsymbol(self, v):
        var = v[1].value
        value = True
        if len(v) > 2:
            value = v[2]

        result = value + [
            Instruction('SET', var)
        ]

        #print(f"node setsymbol  {result}", file=sys.stderr)
        return result

    def body(self, v):
        result = [ Instruction('EMIT', x.value) for x in v ]
        #print(f"node body  {result}", file=sys.stderr)
        return result

    # def execute(self, v):
    #     result = []
    #     for i in v:
    #         if type(i) is callable:
    #             result.extend(i())
    #         else:
    #             result.append(i)
    #     return result

    def condbody(self, v):
        #print(f"* node condbody {v}")
        bexpr = v[1]
        truestart = v[2]
        falsestart = v[4] if len(v)==6 else []

        # if bcond truestart else falsestart
        truecase = self.vm.gensym()
        xcontinue = self.vm.gensym()
        result = bexpr + [
            Instruction('IFJMP', truecase)
        ] + falsestart + [
            Instruction('JMP', xcontinue),
            Instruction('LABEL', truecase)
        ] + truestart + [
            Instruction('LABEL', xcontinue)
        ]

        #print(f"node condbody -> {result}", file=sys.stderr)
        return result

    def condbody2(self, v):
        sym = v[1].value
        truestart = v[2]
        falsestart = v[4] if len(v)==5 else []

        # ifdef sym block1 else block2
        truecase = self.vm.gensym()
        xcontinue = self.vm.gensym()

        result = [
            Instruction('CONST', sym),
            Instruction('EVAL1', 'defined'),
            Instruction('IFJMP', truecase)
        ] + falsestart + [
            Instruction('JMP', xcontinue),
            Instruction('LABEL', truecase)
        ] + truestart + [
            Instruction('LABEL', xcontinue)
        ]

        #print(f"node condbody2 -> {result}", file=sys.stderr)
        return result

    def eval1(self, v):
        #print(f"node eval1 {v}")
        cond = v[0].value
        if v[0].type == 'SYMBOL':
            opcode = 'GET'
        elif v[0].type == 'STRING':
            opcode = 'CONST'
            cond = unwrap_str(cond)
        value = [ Instruction(opcode, cond) ]
        #print(f"node eval1 {value}", file=sys.stderr)
        return value

    def expr1(self, v):
        if v[0].type == 'UNARY':
            # ! a
            a = v[1]
            arg1 = v[0].value
        elif v[0].type == 'DEFINED':
            # defined ( a )
            a = v[2]
            arg1 = 'defined'
        result = a + [ Instruction('EVAL1', arg1) ]
        #print(f"node expr1 {result}", file=sys.stderr)
        return result

    def expr2(self, v):
        a = v[0]
        cmp = v[1].value
        b = v[2]
        result = b + a + [ Instruction('EVAL2', cmp) ]
        #print(f"node expr2 {result}", file=sys.stderr)
        return result


def preprocess(fp : Fpos, environ : dict={}) -> str:
    """- Runs the preprocessor on the input file 'fp' and returns the result as a string
    Args:
        fp :Fpos: The file to be read from
        environ :Dict[str, str]: The initial environment defines
    """
    # Generate preprocessor script from input and execute the script in a VM
    vm = PreprocessorVM(environ)
    parser = Lark(preprocessor_bnf, parser='lalr', lexer=PreprocessorLexer)
    tree = parser.parse(fp)
    #print(tree)
    vm.prog(ParsePreprocessor(vm).transform(tree))
    vm.execute()
    return "".join(vm.output)


def main(args : Arglist):
    app = args.shift()
    print("app", app)
    #process options
    env = {}
    opt = args.shift()
    # print("opt", opt)
    while opt == "-D":
        var,val = args.shift().split('=', 1)
        #print("var,val", var,val)
        env[var] = val
        opt = args.shift()
        #print(opt)
    template_file = opt
    print(template_file)
    if not os.path.isfile(template_file):
        usage()

    # read template
    #print(f"reading {template_file}")
    fp = Fpos(template_file)

    # process template
    body = find_replace_variables(preprocess(fp, env))
    errors.exit_on_error()

    # write output
    if template_file.endswith(".template"):
        output_file = template_file[:-9]
        print(f"writing {output_file}")
        with open(output_file, "wt") as f:
            f.write(body)
    else:
        print(body)

if __name__ == "__main__":
    main(Arglist(sys.argv))