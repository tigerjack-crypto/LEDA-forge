# Needed for matplotlib to run without GUI
# import matplotlib as mpl
# mpl.use('Agg')
# import matplotlib.pyplot as plt

import os
from typing import Sequence

import numpy as np
import plotly.graph_objects as go
# from plotly.subplots import make_subplots
import plotly.io as pio
from isdleda.launchers.launch_data_analysis import AES_LAMBDAS, QAES_LAMBDAS
from isdleda.launchers.launcher_utils import MemAccess
from isdleda.utils.export.export import load_from_pickle
from isdleda.utils.paths import OUT_PLOTS_DATA_DIR, OUT_PLOTS_DIR


def plot_data_plotly(qvals_dic: dict, title: str, out_file_name: str, lambda_vals: Sequence[int]):
    min_first = np.inf
    max_first = 0
    min_second = np.inf
    max_second = 0

    colors = ('blue', 'purple', 'green', 'orange', 'violet')
    fig = go.Figure()
    for idx, (ratio, values) in enumerate(qvals_dic.items()):
        # n, k, t, time
        # selected_values = 
        first_values, _, second_values, third_values = zip(*values[::10])
        fig.add_trace(
            go.Scatter3d(
                x=first_values,
                y=second_values,
                z=third_values,
                mode='markers',
                marker=dict(size=4, color=colors[idx]),
                name=ratio,
                hovertemplate=
                '<b>n</b>: %{x}<br><b>weight</b>: %{y}<br><b>time</b>: %{z}<extra>%{fullData.name}</extra>'  # Custom hover text
            ))
        _val = min(first_values)
        if _val < min_first:
            min_first = _val
        _val = max(first_values)
        if _val > max_first:
            max_first = _val
        _val = min(second_values)
        if _val < min_second:
            min_second = _val
        _val = max(second_values)
        if _val > max_second:
            max_second = _val

        # Create a meshgrid for the plane
        x = np.linspace(min_first, max_first, 10)
        y = np.linspace(min_second, max_second, 10)
        x, y = np.meshgrid(x, y)

        z1 = np.full_like(x, lambda_vals[0])
        z2 = np.full_like(x, lambda_vals[1])
        z3 = np.full_like(x, lambda_vals[2])

        fig.add_trace(
            go.Surface(x=x,
                       y=y,
                       z=z1,
                       name="Level 1",
                       colorscale=[[0, 'red'], [1, 'red']],
                       opacity=0.5,
                       hoverinfo="none",
                       showscale=False))
        fig.add_trace(
            go.Surface(x=x,
                       y=y,
                       z=z2,
                       name="Level 3",
                       colorscale=[[0, 'red'], [1, 'red']],
                       opacity=0.5,
                       hoverinfo="skip",
                       showscale=False))
        fig.add_trace(
            go.Surface(x=x,
                       y=y,
                       z=z3,
                       name="Level 5",
                       colorscale=[[0, 'red'], [1, 'red']],
                       opacity=0.5,
                       hoverinfo="skip",
                       showscale=False))

        # Set labels and title
        fig.update_layout(title=f"{title}",
                          scene=dict(xaxis_title='n',
                                     yaxis_title='weight',
                                     zaxis_title='time'),
                          legend_title="Rate")

        # Save each figure as an HTML file
        html_filename = f"{OUT_PLOTS_DIR}/{out_file_name}.html"
        print(f"Plotting to {html_filename}")
        pio.write_html(fig, file=html_filename, include_plotlyjs='cdn')

def plot_eb():
    for mem_access in MemAccess:
        vals_dic = load_from_pickle(
            os.path.join("sshfs_mountpoint", "vc", "isd-leda",
                         OUT_PLOTS_DATA_DIR, f"cisd_eb_{mem_access.name}"))
        plot_data_plotly(vals_dic, f"EB tool - {mem_access.name}",
                         f"cisd_eb_{mem_access.name}", AES_LAMBDAS)
def plot_qlb():
    vals_dic = load_from_pickle(
        os.path.join("sshfs_mountpoint", "vc", "isd-leda", OUT_PLOTS_DATA_DIR,
                     "q_lb"))
    plot_data_plotly(vals_dic, "PBP - Quantum L-B", "q_lb", QAES_LAMBDAS)

def plot_ledatool():
    for key in ("classic", "quantum"):
        vals_dic = load_from_pickle(
            os.path.join("sshfs_mountpoint", "vc", "isd-leda", OUT_PLOTS_DATA_DIR,
                        f"ledatools_{key}"))
        plot_data_plotly(vals_dic, "LEDAtool", f"LEDAtool_{key}", QAES_LAMBDAS)

def plot_ledatool_ledaparams():
    for key in ("classic", "quantum"):
        vals_dic = load_from_pickle(
            os.path.join("sshfs_mountpoint", "vc", "isd-leda", OUT_PLOTS_DATA_DIR,
                        f"ledatools_ledaparams_{key}"))
        plot_data_plotly(vals_dic, "LEDAtool - LEDA params", f"LEDAtool_ledaparams_{key}", QAES_LAMBDAS)

def main():
    # plot_eb()
    # plot_qlb()
    # plot_ledatool()
    plot_ledatool_ledaparams()


if __name__ == '__main__':
    main()
