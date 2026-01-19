import re
import sys
import subprocess
import os

# Mappings for special types methods
SPECIAL_TYPES = {
    "resource.Quantity": "Equal",
    "metav1.Time": "Equal",
    "metav1.MicroTime": "Equal",
}

# Types that can be compared with ==
COMPARABLE_TYPES = [
    "intstr.IntOrString",
]

# External types that we will fall back to reflect or manual
EXTERNAL_TYPES = [
    "metav1.ObjectMeta",
    "metav1.LabelSelector",
    "metav1.OwnerReference",
    "metav1.NamespaceSelector", # Used in PodAffinityTerm
]

def parse_types(content):
    structs = {}
    maps = {}
    lines = content.split('\n')
    current_struct = None

    struct_start_re = re.compile(r'^type\s+(\w+)\s+struct\s+\{')
    map_type_re = re.compile(r'^type\s+(\w+)\s+map\[([\w\.]+)\]([\w\.]+)')
    # Updated field regex to capture map types and other complex types
    field_re = re.compile(r'^\s+(\w+)\s+([^`\s]+)')
    end_re = re.compile(r'^\}')

    for line in lines:
        match = map_type_re.match(line)
        if match:
            name = match.group(1)
            key_type = match.group(2)
            val_type = match.group(3)
            maps[name] = (key_type, val_type)
            continue

        match = struct_start_re.match(line)
        if match:
            current_struct = match.group(1)
            structs[current_struct] = []
            continue

        if current_struct:
            if end_re.match(line):
                current_struct = None
                continue

            line = line.split('//')[0]
            match = field_re.match(line)
            if match:
                field_name = match.group(1)
                field_type = match.group(2)
                structs[current_struct].append((field_name, field_type))

    return structs, maps

def generate_equal_method(name, fields, all_struct_names, all_maps):
    lines = []
    lines.append(f"func {name}Equal(a, b corev1.{name}) bool {{")

    for fname, ftype in fields:
        is_ptr = ftype.startswith('*')
        base_type = ftype[1:] if is_ptr else ftype

        is_slice = base_type.startswith('[]')
        elem_type = base_type[2:] if is_slice else base_type

        is_map = base_type.startswith('map[')

        a_val = f"a.{fname}"
        b_val = f"b.{fname}"

        if is_ptr:
            lines.append(f"\tif (a.{fname} == nil) != (b.{fname} == nil) {{ return false }}")
            lines.append(f"\tif a.{fname} != nil {{")
            a_val = f"*a.{fname}"
            b_val = f"*b.{fname}"
            indent = "\t\t"
        else:
            indent = "\t"

        if is_slice:
            lines.append(f"{indent}if len({a_val}) != len({b_val}) {{ return false }}")
            lines.append(f"{indent}for i := range {a_val} {{")

            a_elem = f"{a_val}[i]"
            b_elem = f"{b_val}[i]"

            if elem_type.startswith('*'):
                 elem_base = elem_type[1:]
                 lines.append(f"{indent}\tif ({a_elem} == nil) != ({b_elem} == nil) {{ return false }}")
                 lines.append(f"{indent}\tif {a_elem} != nil {{")
                 if elem_base in all_struct_names:
                     lines.append(f"{indent}\t\tif !{elem_base}Equal(*{a_elem}, *{b_elem}) {{ return false }}")
                 elif elem_base in SPECIAL_TYPES:
                     lines.append(f"{indent}\t\tif !{a_elem}.{SPECIAL_TYPES[elem_base]}(*{b_elem}) {{ return false }}")
                 elif elem_base in COMPARABLE_TYPES:
                     lines.append(f"{indent}\t\tif *{a_elem} != *{b_elem} {{ return false }}")
                 else:
                     lines.append(f"{indent}\t\tif *{a_elem} != *{b_elem} {{ return false }}")
                 lines.append(f"{indent}\t}}")
            else:
                 if elem_type in all_struct_names:
                     lines.append(f"{indent}\tif !{elem_type}Equal({a_elem}, {b_elem}) {{ return false }}")
                 elif elem_type in SPECIAL_TYPES:
                     lines.append(f"{indent}\tif !{a_elem}.{SPECIAL_TYPES[elem_type]}({b_elem}) {{ return false }}")
                 elif elem_type in COMPARABLE_TYPES:
                     lines.append(f"{indent}\tif {a_elem} != {b_elem} {{ return false }}")
                 elif elem_type in EXTERNAL_TYPES:
                     lines.append(f"{indent}\tif !reflect.DeepEqual({a_elem}, {b_elem}) {{ return false }}")
                 else:
                     lines.append(f"{indent}\tif {a_elem} != {b_elem} {{ return false }}")

            lines.append(f"{indent}}}") # End for

        elif is_map:
             m = re.match(r'map\[([\w\.]+)\]([\w\.]+)', base_type)
             if m:
                 key_type = m.group(1)
                 val_type = m.group(2)
                 lines.append(f"{indent}if len({a_val}) != len({b_val}) {{ return false }}")
                 lines.append(f"{indent}for k, v := range {a_val} {{")
                 lines.append(f"{indent}\tif v2, ok := {b_val}[k]; !ok || v != v2 {{ return false }}")
                 lines.append(f"{indent}}}")
             else:
                 lines.append(f"{indent}if !reflect.DeepEqual({a_val}, {b_val}) {{ return false }}")

        else:
            if base_type in all_maps:
                lines.append(f"{indent}if !{base_type}Equal({a_val}, {b_val}) {{ return false }}")

            elif base_type in all_struct_names:
                 lines.append(f"{indent}if !{base_type}Equal({a_val}, {b_val}) {{ return false }}")
            elif base_type in SPECIAL_TYPES:
                 lines.append(f"{indent}if !{a_val}.{SPECIAL_TYPES[base_type]}({b_val}) {{ return false }}")
            elif base_type in COMPARABLE_TYPES:
                 lines.append(f"{indent}if {a_val} != {b_val} {{ return false }}")
            elif base_type in EXTERNAL_TYPES:
                 lines.append(f"{indent}if !reflect.DeepEqual({a_val}, {b_val}) {{ return false }}")
            else:
                 lines.append(f"{indent}if {a_val} != {b_val} {{ return false }}")

        if is_ptr:
            lines.append("\t}")

    lines.append("\treturn true")
    lines.append("}")
    return "\n".join(lines)

def generate_map_equal(name, key_type, val_type):
    lines = []
    lines.append(f"func {name}Equal(a, b corev1.{name}) bool {{")
    lines.append(f"\tif len(a) != len(b) {{ return false }}")
    lines.append(f"\tfor k, v := range a {{")

    if val_type in SPECIAL_TYPES:
         lines.append(f"\t\tif v2, ok := b[k]; !ok || !v.{SPECIAL_TYPES[val_type]}(v2) {{ return false }}")
    elif val_type == "resource.Quantity":
         lines.append(f"\t\tif v2, ok := b[k]; !ok || !v.Equal(v2) {{ return false }}")
    else:
         lines.append(f"\t\tif v2, ok := b[k]; !ok || v != v2 {{ return false }}")

    lines.append(f"\t}}")
    lines.append("\treturn true")
    lines.append("}")
    return "\n".join(lines)


def main():
    try:
        cmd = ["go", "list", "-f", "{{.Dir}}", "k8s.io/api/core/v1"]
        out = subprocess.check_output(cmd, text=True).strip()
        if not out:
             print("Error: Could not find package k8s.io/api/core/v1", file=sys.stderr)
             sys.exit(1)
        types_path = os.path.join(out, "types.go")
    except Exception as e:
        print(f"Error finding k8s.io/api/core/v1: {e}", file=sys.stderr)
        sys.exit(1)

    with open(types_path, "r") as f:
        content = f.read()

    structs, maps = parse_types(content)

    queue = ["PodSpec"]
    seen = set()
    ordered = []

    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)

        if name in structs:
            for fname, ftype in structs[name]:
                base = ftype.replace("[]", "").replace("*", "")
                if base in maps:
                    if base not in seen:
                        queue.append(base)
                    continue
                if base.startswith("map["):
                    pass
                if base in structs and base not in seen:
                    queue.append(base)

        elif name in maps:
            _, val_type = maps[name]
            base = val_type.replace("*", "")
            if base in structs and base not in seen:
                queue.append(base)

    print("// Code generated by hack/generate_podspec_equal.py. DO NOT EDIT.")
    print("package workloadmanager")
    print("")
    print("import (")
    print('\tcorev1 "k8s.io/api/core/v1"')
    print('\t"reflect"')
    print(")")
    print("")

    for name in ordered:
        if name in structs:
            print(generate_equal_method(name, structs[name], structs, maps))
            print("")
        elif name in maps:
            k, v = maps[name]
            print(generate_map_equal(name, k, v))
            print("")

if __name__ == "__main__":
    main()
