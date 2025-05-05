import os

import plotly.graph_objects as go
# from plotly.subplots import make_subplots
import plotly.io as pio
from isdleda.utils.export.export import load_from_pickle
from isdleda.utils.paths import OUT_PLOTS_DATA_DIR, OUT_PLOTS_DIR


def plot_data_plotly_complexities(values_list: dict, title: str,
                                  out_file_name: str):

    # colors = ('blue', 'purple', 'green', 'orange', 'violet')
    fig = go.Figure()
    ps, n0s, ts, vs, complexity = zip(*values_list)

    fig.add_trace(
        go.Scatter3d(
            x=ps,
            y=ts,
            z=vs,
            mode='markers',
            marker=dict(
                size=4,
                color=complexity,  # Set marker color based on complexity values
                colorscale='RdBu_r',  # Color scale from red to blue
                colorbar=dict(
                    title='Complexity')  # Add a color bar for reference
            ),
            # Add hover text or other attributes if needed
            # hovertemplate='<b>p</b>: %{x}<br><b>t</b>: %{y}<br><b>v</b>: %{z}<br><b>complexity</b>: %{marker.color}<extra></extra>',
            hovertemplate=(
            '<b>p</b>: %{x}<br>'
            '<b>t</b>: %{y}<br>'
            '<b>v</b>: %{z}<br>'
            '<b>Complexity</b>: %{marker.color}<br>'
            '<extra></extra>'  # Remove the default trace name from the hover label
        )
        ))

    # Set labels and title
    # Update layout to include customized 3D grid and background
    fig.update_layout(scene=dict(
        xaxis=dict(
            title='p',  # Title for the x-axis
            gridcolor=
            'LightSlateGray',  # Color of the grid lines (light gray for contrast)
            zerolinecolor='SlateGray',  # Color of the zero lines
            backgroundcolor='DimGray',  # Dark background color
            showgrid=True,  # Show grid lines
            showline=True,  # Show axis lines
            showbackground=True,  # Show background
            showticklabels=True  # Show axis labels
        ),
        yaxis=dict(
            title='t',  # Title for the y-axis
            gridcolor='LightSlateGray',
            zerolinecolor='SlateGray',
            backgroundcolor='DimGray',
            showgrid=True,
            showline=True,
            showbackground=True,
            showticklabels=True),
        zaxis=dict(
            title='v',  # Title for the z-axis
            gridcolor='LightSlateGray',
            zerolinecolor='SlateGray',
            backgroundcolor='DimGray',
            showgrid=True,
            showline=True,
            showbackground=True,
            showticklabels=True)))

    # Save each figure as an HTML filef"
    html_filename = f"{OUT_PLOTS_DIR}/{out_file_name}.html"
    print(f"Plotting to {html_filename}")
    pio.write_html(fig, file=html_filename, include_plotlyjs='cdn')


def plot_ledatool_ledaparams():
    # vals_dic = load_from_pickle(
    #     os.path.join("sshfs_mountpoint", "vc", "isd-leda", OUT_PLOTS_DATA_DIR,
    #                  f"ledatools_ledaparams_exploration_all"))
    # for rate, vals in vals_dic.items():
    #     print(f"Rate {rate}, len vals {len(vals)}")

    #     plot_data_plotly_all(
    #         vals, f"LEDAtool - LEDA params exploration - Level {rate}",
    #         f"LEDAtool_ledaparams_exploration_{rate}_all")

    c_vals_dic = load_from_pickle(
        os.path.join("sshfs_mountpoint", "vc", "isd-leda", OUT_PLOTS_DATA_DIR,
                     f"ledatools_ledaparams_exploration_classic"))
    for rate, vals in c_vals_dic.items():
        print(f"Rate {rate}, len vals {len(vals)}")
        plot_data_plotly_complexities(
            vals,
            f"LEDAtool - LEDA params exploration - Level {rate} - Classic",
            f"LEDAtool_ledaparams_exploration_{rate}_classic")

    q_vals_dic = load_from_pickle(
        os.path.join("sshfs_mountpoint", "vc", "isd-leda", OUT_PLOTS_DATA_DIR,
                     f"ledatools_ledaparams_exploration_quantum"))
    for rate, vals in q_vals_dic.items():
        print(f"Rate {rate}, len vals {len(vals)}")
        plot_data_plotly_complexities(
            vals,
            f"LEDAtool - LEDA params exploration - Level {rate} - Quantum",
            f"LEDAtool_ledaparams_exploration_{rate}_quantum")


def main():
    plot_ledatool_ledaparams()


if __name__ == '__main__':
    main()
