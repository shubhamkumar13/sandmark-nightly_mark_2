from re import U, split, sub
import streamlit as st
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

def app():
    st.title("Parallel Benchmarks")

    class BenchStruct:
        config = {}

        def __init__(self):
            self.structure = nested_dict(3, list)
            self.config["bench_type"] = "parallel"
            self.config["artifacts_dir"] = "/Users/shubham/sandmark-nightly"
            self.config["bench_stem"] = "_1.orunchrt.summary.bench"


        def add(self, host, timestamp, commit, variant):
            self.structure[host][timestamp][commit].append(variant)
        
        def add_files(self, files):
            for x in files:
                l = x.split(str("/" + self.config["bench_type"] + "/"))[1]
                d = l.split("/")
                self.add(
                    d[0],
                    d[1],
                    d[2],
                    d[3]
                )
        
        def to_filepath(self):
            lst = []
            temp = ""
            for host, timestamps in self.structure.items():
                for timestamp, commits in timestamps.items():
                    for commit, bench_files in commits.items():
                        t = [self.config["artifacts_dir"] + "/" + self.config["bench_type"] + "/" + str(host) + "/" + str(timestamp) + "/" + str(commit) + "/" + str(bench_file) for bench_file in bench_files]
                        lst.append(t)
            return lst

        def get_bench_files(self):
            bench_files = []
            for root, dirs, files in os.walk(benches.config["artifacts_dir"] + "/" + benches.config["bench_type"]):
                for file in files:
                    if file.endswith(self.config["bench_stem"]):
                        f = root.split("/" + self.config["bench_type"] + "/")
                        bench_files.append((os.path.join(root, file)))
            return bench_files

        def __repr__(self):
            return f'{self.structure}'
    
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
        # print(a[1])
        (x, y) = a[0], flatten(a[1])
        return (x, y)

    def fmt_variant(commit, variant):
        return (variant.split('_')[0] + '+' + str(commit) + '_' + variant.split('_')[1])

    def unfmt_variant(variant):
        commit = variant.split('_')[0].split('+')[-1]
        variant_root = variant.split('_')[1]
        variant_stem = variant.split('_')[0].split('+')
        variant_stem.pop()
        variant_stem = reduce(lambda a, b: b if a == "" else a + "+" + b, variant_stem, "")
        new_variant = variant_stem + '_' + variant_root
        # st.write(new_variant)
        return (commit , new_variant)

    def get_selected_values(n):
        lst = []
        for i in range(n):
            # create the selectbox in columns
            host_val = containers[i][0].selectbox('hostname', benches.structure.keys(), key = str(i) + '0_sequential')
            timestamp_val = containers[i][1].selectbox('timestamp', benches.structure[host_val].keys(), key = str(i) + '1_sequential')
            commits, variants = unzip_dict((benches.structure[host_val][timestamp_val]).items())
            # st.write(variants)
            fmtted_variants = [fmt_variant(c, v) for c,v in zip(commits, variants)]
            # st.write(fmtted_variant)
            variant_val = containers[i][2].selectbox('variant', fmtted_variants, key = str(i) + '2_sequential')
            selected_commit, selected_variant = unfmt_variant(variant_val)
            lst.append({"host" : host_val, "timestamp" : timestamp_val, "commit" : selected_commit, "variant" : selected_variant})
        return lst

    selected_benches = BenchStruct()
    _ = [selected_benches.add(f["host"], f["timestamp"], f["commit"], f["variant"]) for f in get_selected_values(n)]


    # Expander for showing bench files
    with st.expander("Show metadata of selected benchmarks"):
        st.write(selected_benches.structure)

    selected_files = flatten(selected_benches.to_filepath())

    def get_dataframe(file):
        # json to dataframe

        with open(file) as f:
            data = []
            for l in f:
                data.append(json.loads(l))
            df = pdjson.json_normalize(data)
            value     = file.split('/' + benches.config["bench_type"] + '/')[1]
            date      = value.split('/')[1].split('_')[0]
            commit_id = value.split('/')[2][:7]
            variant   = value.split('/')[3].split('_')[0]
            df["variant"] = variant + '_' + date + '_' + commit_id
        
        return df


    def get_dataframes_from_files(files):
        data_frames = [get_dataframe(file) for file in files]
        df = pd.concat (data_frames, sort=False)
        df = df.sort_values(['name', 'time_secs'])
        return df

    df = get_dataframes_from_files(selected_files)
    
    def getFastestSequential(df,topic):
        fastest_sequential = {}
        for g in df.groupby(['name']):
            (n,d) = g
            fastest_sequential[n] = min(list(d[topic]))
        return fastest_sequential

    def normalize(sdf, mdf, topic):
        frames = []
        fastest_sequential = getFastestSequential(sdf, topic)
        for g in mdf.groupby('name'):        
            (n,d) = g
            n = n.replace('_multicore','')
            d['n'+topic] = 1 / d[topic].div(fastest_sequential[n],axis=0)
            d['b'+topic] = int(fastest_sequential[n])
            frames.append(d)
        return pd.concat(frames)


    # Sequential runs
    sdf = df.loc[~df['name'].str.contains('multicore',regex=False),:]
    throughput_sdf = pd.DataFrame.copy(sdf)
    with st.expander("Show Raw data (sequential runs)"):
        st.write(sdf)

    # Multicore runs
    mdf = df.loc[df['name'].str.contains('multicore',regex=False),:]
    mdf['num_domains'] = mdf['name'].str.split('.',expand=True)[1].str.split('_',expand=True)[0]
    mdf['num_domains'] = pd.to_numeric(mdf['num_domains'])
    mdf['name'] = mdf['name'].replace('\..*?_','.',regex=True)

    mdf = normalize(sdf,mdf,"time_secs")
    throughput_mdf = pd.DataFrame.copy(mdf)
    with st.expander("Show Raw data (multicore runs)"):
        st.write(mdf)
    # mdf.sort_values(['name','variant','num_domains'])

    mdf = mdf.sort_values(['name'])
    time_g = sns.relplot(x='num_domains', y = 'time_secs', hue='variant', col='name',
            data=mdf, kind='line', style='variant', markers=True, col_wrap = 5, 
            lw=5, palette="muted")
    
    st.header("Time")
    st.pyplot(time_g)

    mdf = mdf.sort_values(['name'])
    with sns.plotting_context(rc={"font.size":14,"axes.titlesize":14,"axes.labelsize":14, "legend.fontsize":14}):
        speedup_g = sns.relplot(x='num_domains', y = 'ntime_secs', hue='variant', col='name',
                data=mdf, kind='line', style='variant', markers=True, col_wrap = 5, 
                lw=3)
    
    st.header("Speedup")
    st.pyplot(speedup_g)