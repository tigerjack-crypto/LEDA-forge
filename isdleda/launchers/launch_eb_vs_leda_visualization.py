import csv
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
import pandas as pd

# from plotly.subplots import make_subplots


def main():
    data = []
    with open('out/eb_vs_leda_diff.csv', newline='') as csvfile:
        reader = csv.reader(csvfile,
                            delimiter=',',
                            quotechar='|',
                            quoting=csv.QUOTE_MINIMAL)
        headers = next(reader)
        for row in reader:
            data.append(row)

    # Convert data to a DataFrame for easier manipulation
    df = pd.DataFrame(data, columns=headers)
    df = df.astype({
        'n': 'int',
        'r': 'int',
        't': 'int',
        'EB Stern': 'float',
        'LEDA Stern': 'float',
        'EB Stern p': 'int',
        'EB Stern l': 'int',
        'EB Stern M4R': 'int',
        'LEDA Stern p': 'int',
        'LEDA Stern l': 'int'
    })
    # ns = []
    # ks = []
    # ts = []
    # vals = []
    # for val in data:
    #     ns = data

    # Convert appropriate columns to numeric types
    df['n'] = df['n'].astype(int)
    df['r'] = df['r'].astype(int)
    df['t'] = df['t'].astype(int)
    df['EB Stern'] = df['EB Stern'].astype(float)
    df['LEDA Stern'] = df['LEDA Stern'].astype(float)
    df['EB Stern p'] = df['EB Stern p'].astype(int)
    df['EB Stern l'] = df['EB Stern l'].astype(int)
    df['EB Stern M4R'] = df['EB Stern M4R'].astype(int)
    df['LEDA Stern p'] = df['LEDA Stern p'].astype(int)
    df['LEDA Stern l'] = df['LEDA Stern l'].astype(int)

    # Calculate the difference and the ratio
    df['Difference'] = df['EB Stern'] - df['LEDA Stern']
    df['k'] = df['n'] - df['r']
    df['Ratio'] = df['k'] / df['n']

    fig = go.Figure()
    # Create the 3D scatter plot
    # fig.add_trace(
    #     go.Scatter3d(
    #         x=df['n'],
    #         y=df['t'],
    #         z=df['Difference'],
    #         mode='markers',
    #     ))

    # Create the 3D scatter plot
    fig = px.scatter_3d(df,
                        x='n',
                        y='t',
                        z='Difference',
                        color='Ratio',
                        color_continuous_scale='Viridis',  # Use the 'Viridis' color scale
                        hover_data=df.columns,
                        labels={'Difference': 'EB - LEDA'})

    # Show the plot
    # fig.show()

    # Export the plot as an image
    # fig.write_image("3d_plot.png")

    # # Show the plot
    pio.write_html(fig, file='out/plots/eb_vs_leda.html', include_plotlyjs='cdn')


if __name__ == '__main__':
    main()
