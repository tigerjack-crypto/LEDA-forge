# Needed for matplotlib to run without GUI
# import matplotlib as mpl
# mpl.use('Agg')

import os

# import matplotlib.pyplot as plt

import numpy as np
import plotly.graph_objects as go
# from plotly.subplots import make_subplots
import plotly.io as pio

from isdleda.utils.export.export import load_from_pickle
from isdleda.utils.paths import OUT_PLOTS_DIR, OUT_PLOTS_DATA_DIR


def plot_data_plotly(cvals: list[dict]):
    for idx, cvals_tup in enumerate(cvals):
        mem, cvals_dic = cvals_tup
        fig = go.Figure()

        min_first = np.inf
        max_first = 0
        min_second = np.inf
        max_second = 0
        for ratio, values in cvals_dic.items():
            first_values, _, second_values, third_values = zip(*values)
            fig.add_trace(
                go.Scatter3d(
                    x=first_values,
                    y=second_values,
                    z=third_values,
                    mode='markers',
                    marker=dict(size=2),
                    name=ratio,
                    showlegend=False,
                ))
            # Dummy trace for the legend with larger markers
            fig.add_trace(
                go.Scatter3d(
                    x=[None],
                    y=[None],
                    z=[None],
                    mode='markers',
                    name=ratio,
                    marker=dict(size=10),  # Larger markers for the legend
                    showlegend=True,
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
        z1 = np.full_like(x, 143)
        z2 = np.full_like(x, 207)
        z3 = np.full_like(x, 272)

        fig.add_trace(
            go.Surface(x=x,
                       y=y,
                       z=z1,
                       colorscale=[[0, 'red'], [1, 'red']],
                       opacity=0.5,
                       showscale=False))
        fig.add_trace(
            go.Surface(x=x,
                       y=y,
                       z=z2,
                       colorscale=[[0, 'red'], [1, 'red']],
                       opacity=0.5,
                       showscale=False))
        fig.add_trace(
            go.Surface(x=x,
                       y=y,
                       z=z3,
                       colorscale=[[0, 'red'], [1, 'red']],
                       opacity=0.5,
                       showscale=False))

        # Set labels and title
        fig.update_layout(title=mem,
                          scene=dict(xaxis_title='n',
                                     yaxis_title='weight',
                                     zaxis_title='time'),
                          legend_title="n0")

        # Save each figure as an HTML file
        html_filename = f"{OUT_PLOTS_DIR}/plot_{idx+1}.html"
        pio.write_html(fig, file=html_filename, include_plotlyjs='cdn')


def main():
    cvals_dic = load_from_pickle(
        os.path.join("sshfs_mountpoint", "vc", "isd-leda", OUT_PLOTS_DATA_DIR,
                     "all"))
    plot_data_plotly(cvals_dic)


if __name__ == '__main__':
    main()



# def plot_data_matplotlib(cvals: list[dict]):
#     # fig = plt.figure()
#     # axs = fig.subplots(ncols=2, nrows=len(cvals) // 2 + len(cvals) % 2, subplot_kw={'projection': '3d'})
#     # axs = axs.flatten()

#     # for (ax, cvals_tup) in zip(axs, cvals):
#     for cvals_tup in cvals:
#         fig = plt.figure()
#         mem, cvals_dic = cvals_tup
#         ax = fig.add_subplot(projection='3d')
#         ax.set_title(mem)

#         min_first = np.inf
#         max_first = 0
#         min_second = np.inf
#         max_second = 0
#         for ratio, values in cvals_dic.items():
#             first_values, _, second_values, third_values = zip(*values)
#             ax.scatter(first_values, second_values, third_values, label=ratio)
#             _val = min(first_values)
#             if _val < min_first:
#                 min_first = _val
#             _val = max(first_values)
#             if _val > max_first:
#                 max_first = _val
#             _val = min(second_values)
#             if _val < min_second:
#                 min_second = _val
#             _val = max(second_values)
#             if _val > max_second:
#                 max_second = _val

#         # Set labels
#         ax.set_xlabel('n')
#         ax.set_ylabel('weight')
#         ax.set_zlabel('time')

#         # Create a meshgrid for the plane
#         x = np.linspace(min_first, max_first, 10)
#         y = np.linspace(min_second, max_second, 10)
#         x, y = np.meshgrid(x, y)
#         z1 = np.full_like(x, 143)
#         z2 = np.full_like(x, 207)
#         z3 = np.full_like(x, 272)

#         ax.plot_surface(x, y, z1, color='r', alpha=.5)
#         ax.plot_surface(x, y, z2, color='r', alpha=.5)
#         ax.plot_surface(x, y, z3, color='r', alpha=.5)
#         ax.legend()
#         # fig.savefig(f"out/figs/{mem}.png")
#         # save_to_pickle(os.path.join(OUT_FIGURE_DIR, f"{mem}.fig.pkl"), fig)

#         plt.show()
