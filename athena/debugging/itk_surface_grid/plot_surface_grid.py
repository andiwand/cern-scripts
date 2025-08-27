import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os

def plot_local_positions(grid_file, surface_file, output_pdf):
    # Load the data
    grid_df = pd.read_csv(grid_file)
    surface_df = pd.read_csv(surface_file)

    # Create the plot
    plt.figure(figsize=(10, 10))
    plt.scatter(grid_df['lx'], grid_df['ly'], label='Grid Positions', s=10 + 20 * grid_df['nSurfaces'], alpha=0.7)
    plt.scatter(surface_df['lx'], surface_df['ly'], label='Surface Positions', s=10, alpha=0.7, marker='x')

    # Plot formatting
    plt.xlabel('Local X (lx)')
    plt.ylabel('Local Y (ly)')
    plt.title('Local Grid and Surface Positions')
    plt.legend()
    plt.grid(True)

    # Save the plot
    plt.savefig(output_pdf)
    plt.close()
    print(f"Saved plot to {output_pdf}")

def main():
    parser = argparse.ArgumentParser(description='Plot local grid and surface positions.')
    parser.add_argument('grid_file', help='CSV file containing grid positions')
    parser.add_argument('surface_file', help='CSV file containing surface positions')
    parser.add_argument('-o', '--output', default='local_positions_plot.pdf', help='Output PDF filename (default: local_positions_plot.pdf)')

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.grid_file):
        print(f"Error: Grid file '{args.grid_file}' does not exist.")
        return
    if not os.path.exists(args.surface_file):
        print(f"Error: Surface file '{args.surface_file}' does not exist.")
        return

    plot_local_positions(args.grid_file, args.surface_file, args.output)

if __name__ == '__main__':
    main()
