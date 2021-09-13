import streamlit as st
from re import U, split, sub
import numpy as np
import pandas as pd
from functools import reduce

from nested_dict import nested_dict
from pprint import pprint

import json
import os
import pandas as pd
import pandas.io.json as pdjson
import seaborn as sns
from apps import benchstruct

def app():
    st.title("Instrumented Pausetimes (sequential)")

	# Problem : right now the structure is a nested dict of
	#     `(hostname * (timestamp * (variants list)) dict ) dict`
	# and this nested structure although works but it is a bit difficult to work with
	# so we need to create a class object which is a record type and add
	# functions to

	# <host 1>
	# |--- <timestamp 1>
	#         |--- <commit 1>
	#                 |--- <variant 1>
	#                 |--- <variant 2>
	#                 ....
	#                 ....
	#                 ....
	#                 |--- <variant n>
	#         |--- <commit 2>
	#                 ....
	#                 ....
	#                 ....
	#         ....
	#         ....
	#         ....
	#         |--- <commit n>
	#                 ....
	#                 ....
	#                 ....
	# ....
	# ....
	# ....
	# ....
	# |--- <timestamp n>
	#         ....
	#         ....
	# <host 2>
	# ....
	# ....
	# ....
	# <host n>

	# This idea is only for sandmark nightly

    class BenchStruct(benchstruct.BenchStruct):
        
        def __init__(self):
            self.structure = nested_dict(3, list)
            self.config["bench_type"] = "sequential"
            self.config["artifacts_dir"] = "/Users/shubham/sandmark-nightly/pausetimes"
            self.config["bench_stem"] = ["_1.pausetimes_trunk.summary.bench","_1.pausetimes_multicore.summary.bench"]
        

        def get_bench_files(self):
            bench_files = []

            # Loads file metadata
            for root, dirs, files in os.walk(self.config["artifacts_dir"] + "/" + self.config["bench_type"]):
                for file in files:
                    if file.endswith(self.config["bench_stem"][0]) or file.endswith(self.config["bench_stem"][1]):
                        f = root.split("/" + self.config["bench_type"])
                        bench_files.append((os.path.join(root,file)))
            
            return bench_files

    benches = BenchStruct()
    benches.add_files(benches.get_bench_files())

    st.header("Select variants")
    n = int(st.text_input('Number of variants','2', key=benches.config["bench_type"]))

    containers = [st.columns(3) for i in range(n)]

    # [[a11, a12 ... a1n], [a21, a22 ... a2n], ... [am1, am2 ... amn]] => [a11]
    def flatten(lst):
        return reduce(lambda a, b: a + b, lst)

    # [(a1, b1), (a2, b2) ... (an, bn)] => ([a1, a2, ... an], [b1, b2, ... bn])
    def unzip(lst):
        return (list(zip(*lst)))

    def unzip_dict(d):
        a = unzip(list(d))
        # st.write(a)
        (x, y) = a[0], flatten(a[1])
        return (x, y)

    def fmt_variant(commit, variant):
        # st.write(variant.split('_'))
        return (variant.split('_')[0] + '+' + str(commit) + '_' + variant.split('_')[1] + '_' + variant.split('_')[2])

    def unfmt_variant(variant):
        commit = variant.split('_')[0].split('+')[-1]
        variant_root = variant.split('_')[1] + '_' + variant.split('_')[2]
        # st.write(variant_root)
        variant_stem = variant.split('_')[0].split('+')
        variant_stem.pop()
        variant_stem = reduce(lambda a, b: b if a == "" else a + "+" + b, variant_stem, "")
        new_variant = variant_stem + '_' + variant_root
        # st.write(new_variant)
        return (commit , new_variant)
    

    def get_selected_values(n):
        lst = []
        for i in range(n):
            
            def check_something():
                host_val = st.session_state[str(i) + '0_' + benches.config["bench_type"]]
                timestamp_val = st.session_state[str(i) + '1_' + benches.config["bench_type"]]
                if (benches.structure[host_val][timestamp_val]).items():
                    print("right")
                else:
                    print("wrong")
                
            # create the selectbox in columns
            host_val = containers[i][0].selectbox('hostname', benches.structure.keys(), key = str(i) + '0_' + benches.config["bench_type"], on_change=check_something)
            timestamp_val = containers[i][1].selectbox('timestamp', benches.structure[host_val].keys(), key = str(i) + '1_' + benches.config["bench_type"])
            # st.write((benches.structure[host_val][timestamp_val]).items())
            if (benches.structure[host_val][timestamp_val]).items():
                commits, variants = unzip_dict((benches.structure[host_val][timestamp_val]).items())
                # st.write(variants)
                fmtted_variants = [fmt_variant(c, v) for c,v in zip(commits, variants)]
                # st.write(fmtted_variants)
                variant_val = containers[i][2].selectbox('variant', fmtted_variants, key = str(i) + '2_' + benches.config["bench_type"])
                selected_commit, selected_variant = unfmt_variant(variant_val)
                lst.append({"host" : host_val, "timestamp" : timestamp_val, "commit" : selected_commit, "variant" : selected_variant})
    
        return lst

    selected_benches = BenchStruct()
    _ = [selected_benches.add(f["host"], f["timestamp"], f["commit"], f["variant"]) for f in get_selected_values(n)]

    # Expander for showing bench files
    with st.expander("Show metadata of selected benchmarks"):
        st.write(selected_benches.structure)

    selected_files = flatten(selected_benches.to_filepath())

    # for i in range(n):