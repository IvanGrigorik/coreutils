import matplotlib.pyplot as plt
import numpy as np
import yaml
from pathlib import Path

CUR_DIR = Path(__file__).parent
ARG_TYPE_PARSED_FILE = CUR_DIR.parent / "scripts" / "out.yaml"
ARG_PARSED_FILE = CUR_DIR.parent.parent / "out.yaml"


def parse_type_file():
    with open(ARG_TYPE_PARSED_FILE, 'r') as file:

        # Content type: [{ str: [ { [str] : {str: str } } ] }]
        content = yaml.safe_load(file)
        commands: dict[str: list[str]] = {}
        for command in content:
            # Gather parsed option types
            parsed_args = []
            for args in content[command]:
                for key in args:
                    key = key.split(',')
                    for k in key:
                        if k not in parsed_args:
                            parsed_args += key
            commands[command] = parsed_args

    return commands


def parse_arg_file():
    with open(ARG_PARSED_FILE, 'r') as file:
        content = yaml.safe_load(file)
        commands: dict[str: dict[str: str]] = {}
        for command in content:
            if (len(content[command]["shortopts"]) <= 0 and len(content[command]["longopts"]) <= 0):
                continue
            required_args: list[str] = []
            optional_args = []

            # Parse short options
            for opt in content[command]["shortopts"]:
                if opt["option"] == "required":
                    required_args += opt["name"]
                if opt["option"] == "optional":
                    optional_args += opt["name"]

            # Parse long options
            for opt in content[command]["longopts"]:
                if (opt["option"] == "required" and
                        opt["char"] not in required_args):
                    required_args.append(opt["name"])
                if (opt["option"] == "optional" and
                    opt["char"] not in optional_args or
                        opt["char"] not in required_args):
                    optional_args.append(opt["name"])
            commands[command] = {}
            commands[command]["required"] = required_args
            commands[command]["optional"] = optional_args

    return commands


def merge(typed: dict[str: list[str]], parsed: dict[str: dict[str: str]]) -> dict[str: dict[str:list]]:
    merged = {}

    for command in parsed:
        merged[command] = {}
        merged[command]["parsed"] = []
        merged[command]["not parsed"] = parsed[command]["required"]
        # print(merged[command])

    for command in typed:
        merged[command]["parsed"].extend(typed[command])
        merged[command]["not parsed"] = [x for x in merged[command]["not parsed"]
                                         if x not in merged[command]["parsed"]]

    return merged


# Generates a LaTeX table
def gen_table(merged: dict[str: dict[str:list]]):
    headers = ["Command", "Parsed", "Not parsed"]
    data = dict()
    data["command"] = [x for x in merged]
    data["parsed"] = [merged[x]["parsed"] for x in merged]
    data["not parsed"] = [merged[x]["not parsed"] for x in merged]

    data["parsed"] = [[s.replace("_", r"\_") for s in sublist]
                      for sublist in data["parsed"]]
    data["not parsed"] = [[s.replace("_", r"\_") for s in sublist]
                          for sublist in data["not parsed"]]

    textabular = "|p{0.3\\linewidth}|p{0.4\\linewidth}|p{0.3\\linewidth}|"
    texheader = "& ".join(headers) + "\\\\"
    texdata = "\\hline\n"

    for (label, parsed, non_parsed) in zip(data["command"], data["parsed"], data["not parsed"]):
        if (len(parsed) == 0 and len(non_parsed) == 0):
            continue
        texdata += "\\hline\n"
        texdata += label + ' & '
        if len(parsed) == 0:
            texdata += " \\textit{none} &"
        else:
            texdata += ' '.join(sorted(parsed)) + ' & '

        if len(non_parsed) == 0:
            texdata += " \\textit{none}"
        else:
            texdata += ' '.join(sorted(non_parsed))
        texdata += '\\\\ \n'

    if not texdata.endswith("\\\\ \n"):
        texdata += '\\\\ \n'
    texdata += "\\hline\n"

    out = "\\begin{longtable}{"+textabular+"}" + '\n'
    out += "\\hline\n" + texheader + '\n'
    out += texdata
    out += "\\end{longtable}" + '\n'
    
    return out

def gen_num(merged):
    

def main():
    typed_commands: dict[str: list[str]] = parse_type_file()
    parsed_commands: dict[str: dict[str: str]] = parse_arg_file()

    merged = merge(typed_commands, parsed_commands)

    out = gen_table(merged)
    num = gen_nums(merged)
    with open("table.tex", "w") as file:
        file.truncate()
        file.write(out)


if __name__ == "__main__":
    main()
    parse_arg_file()
