import sys
import jupyter_aws as jaws
from jupyter_aws.known_secret import KnownSecret, SecretId
from foundrysmith.error_report import ErrorReport
import os
import re
import json

errors = ErrorReport()

def usage():
    print("Usage: fill-template.py <templatefile>")
    sys.exit(1)


def replace_variable(body, span, varvalue):
    #print(f"replace_variable(body..., {span}, {varvalue})")
    if varvalue is None:
        varvalue = "NODATA"
    body = body.replace(span, varvalue)
    #print(body)
    return body

def get_secret(varname):
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

def find_replace_variables(body : str):
    while True:
        m = re.search(r"@([a-zA-Z]+):([a-zA-Z_\.-]+)@", body)
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
            else:
                errors.error(f"Unknown variable type: '{vartype}'")
                varvalue = None
            body = replace_variable(body, span, varvalue)
        else:
            break
    return body


def main(args : jaws.Arglist):
    template_file = args.shift()
    if not os.path.isfile(template_file):
        usage()

    #print(f"reading {template_file}")
    with open(template_file, "rt") as f:
        body = find_replace_variables(f.read())
    errors.exit_on_error()

    if template_file.endswith(".template"):
        output_file = template_file[:-9]
        print(f"writing {output_file}")
        with open(output_file, "wt") as f:
            f.write(body)

if __name__ == "__main__":
    main(jaws.Arglist(sys.argv[1:]))