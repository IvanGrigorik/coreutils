import yaml
from pathlib import Path

NONUNIFIED_YAML = Path(__file__).parent / "out" / "nonunified.yaml"
UNIFIED_YAML = Path(__file__).parent / "out" / "unified.yaml"


def unify_attributes(command: str, opts: dict):

    # Create unique instance for each of the option (if the options are CSV)
    opts_map: dict[str: list] = {}

    for option, types in opts.items():
        for option in option.split(','):
            if option in opts_map:
                opts_map[option].extend(types)
            else:
                opts_map[option] = types

    # Get rid of duplicate types and remove all empty options from the list
    for option, types in opts_map.items():
        opts_map[option] = list(set(types))
        opts_map[option] = list(filter(None, opts_map[option]))
        opts_map[option].sort()

    # Connect the options with shared cases
    grouped = {}
    for opt, types_list in opts_map.items():
        key = tuple(types_list)
        if key in grouped:
            grouped[key].append(opt)
        else:
            grouped[key] = [opt]

    merged_map = {}
    for types_tuple, names in grouped.items():
        merged_map[", ".join(names)] = list(types_tuple)

    return merged_map

# unifies the YAML file. For example, if there are two or more options with same
# type but located as a different values - it would combine them into one.


def unify_yaml():
    out_content: dict[str: list[dict]] = {}

    with open(NONUNIFIED_YAML, "r") as file:
        content: dict = yaml.safe_load(file)
        for command, options in content.items():

            # Map the options to the argument types
            opt_map: dict[str: list] = {}

            for option in options:
                for name, attributes in option.items():
                    # print(f"option name: {name}")
                    # print(f"option types: {attributes}")
                    if name not in opt_map:
                        opt_map[name] = []
                    if type(attributes["type"]) == list:
                        opt_map[name].extend(attributes["type"])
                    else:
                        opt_map[name].extend([attributes["type"]])

            opts = unify_attributes(command, opt_map)
            out_content[command] = opts
    return out_content

def print_yaml(content):
    with open(UNIFIED_YAML, 'w') as file:
        file.truncate()
        yaml.dump(content, file)


def main():
    content = unify_yaml()
    print_yaml(content)
    # with open(UNIFIED_YAML, "w") as file:
    #     file.truncate()

    #     file.write(content)
    # pass


if __name__ == "__main__":
    main()
