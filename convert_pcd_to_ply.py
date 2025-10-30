"""
Convert PCD point cloud to PLY format for PointDreamer
- Handles PCD to PLY conversion
- Downsamples to max 30000 points
- Converts color range from [0,1] to [0,255]
"""

import open3d as o3d
import numpy as np
from plyfile import PlyData, PlyElement
import argparse
import os

def convert_pcd_to_ply(pcd_path, output_ply_path=None, max_points=30000, downsample_method='uniform'):
    """
    Convert PCD file to PLY format compatible with PointDreamer

    Args:
        pcd_path: Path to input PCD file
        output_ply_path: Path to output PLY file (if None, auto-generate)
        max_points: Maximum number of points (default 30000)
        downsample_method: 'uniform' or 'voxel'
    """

    # Read PCD file
    print(f"Reading PCD file: {pcd_path}")
    pcd = o3d.io.read_point_cloud(pcd_path)

    # Get points and colors
    points = np.asarray(pcd.points)

    if not pcd.has_colors():
        print("Warning: PCD file has no color information. Using default gray color.")
        colors = np.full((len(points), 3), 0.5)  # Default gray
    else:
        colors = np.asarray(pcd.colors)

    print(f"Original point count: {len(points)}")
    print(f"Point cloud bounds: min={points.min(axis=0)}, max={points.max(axis=0)}")

    # Downsample only if point count exceeds max_points
    if len(points) > max_points:
        print(f"Downsampling from {len(points)} to {max_points} points using {downsample_method} method...")

        if downsample_method == 'uniform':
            # Uniform random sampling
            indices = np.random.choice(len(points), max_points, replace=False)
            points = points[indices]
            colors = colors[indices]

        elif downsample_method == 'voxel':
            # Voxel downsampling (better preserves structure)
            # Estimate voxel size to get approximately max_points
            # Use a smaller multiplier to avoid over-downsampling
            bbox_size = (points.max(axis=0) - points.min(axis=0)).max()
            voxel_size = bbox_size / (max_points ** (1/3)) * 0.5  # Use 0.5x to get more points

            pcd_downsampled = pcd.voxel_down_sample(voxel_size=voxel_size)
            points_voxel = np.asarray(pcd_downsampled.points)
            colors_voxel = np.asarray(pcd_downsampled.colors)

            # If too many points, use uniform sampling to reduce
            if len(points_voxel) > max_points:
                indices = np.random.choice(len(points_voxel), max_points, replace=False)
                points = points_voxel[indices]
                colors = colors_voxel[indices]
            # If too few points, fall back to uniform sampling from original
            elif len(points_voxel) < max_points * 0.5:  # If less than 50% of target
                print(f"Voxel downsampling yielded too few points ({len(points_voxel)}), using uniform sampling instead...")
                indices = np.random.choice(len(points), max_points, replace=False)
                points = points[indices]
                colors = colors[indices]
            else:
                points = points_voxel
                colors = colors_voxel

        print(f"After downsampling: {len(points)} points")
    else:
        print(f"Point count ({len(points)}) is within limit ({max_points}), keeping all original points")

    # Convert color range from [0,1] to [0,255]
    colors_255 = (colors * 255).astype(np.uint8)

    # Verify color range
    print(f"Color range: min={colors_255.min()}, max={colors_255.max()}")
    print(f"Sample colors (first 3 points):\n{colors_255[:3]}")

    # Generate output path if not provided
    if output_ply_path is None:
        output_ply_path = pcd_path.replace('.pcd', '.ply')
        if output_ply_path == pcd_path:  # If no .pcd extension
            output_ply_path = pcd_path + '.ply'

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_ply_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: {output_dir}")

    # Create PLY vertex array
    vertex_data = []
    for i in range(len(points)):
        vertex_data.append((
            float(points[i, 0]), float(points[i, 1]), float(points[i, 2]),
            int(colors_255[i, 0]), int(colors_255[i, 1]), int(colors_255[i, 2])
        ))

    vertex = np.array(vertex_data, dtype=[
        ('x', 'f4'), ('y', 'f4'), ('z', 'f4'),
        ('red', 'u1'), ('green', 'u1'), ('blue', 'u1')
    ])

    # Save PLY file
    el = PlyElement.describe(vertex, 'vertex')
    PlyData([el]).write(output_ply_path)

    print(f"Successfully saved PLY file: {output_ply_path}")
    print(f"Final point count: {len(points)}")

    return output_ply_path


def batch_convert(input_dir, output_dir=None, max_points=30000, downsample_method='uniform'):
    """
    Batch convert all PCD files in a directory
    """
    if output_dir is None:
        output_dir = input_dir

    os.makedirs(output_dir, exist_ok=True)

    pcd_files = [f for f in os.listdir(input_dir) if f.endswith('.pcd')]

    if not pcd_files:
        print(f"No PCD files found in {input_dir}")
        return

    print(f"Found {len(pcd_files)} PCD files")

    for pcd_file in pcd_files:
        pcd_path = os.path.join(input_dir, pcd_file)
        ply_file = pcd_file.replace('.pcd', '.ply')
        ply_path = os.path.join(output_dir, ply_file)

        print(f"\n{'='*60}")
        try:
            convert_pcd_to_ply(pcd_path, ply_path, max_points, downsample_method)
        except Exception as e:
            print(f"Error converting {pcd_file}: {e}")
            continue


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert PCD to PLY for PointDreamer')
    parser.add_argument('input', type=str, help='Input PCD file or directory')
    parser.add_argument('--output', type=str, default=None, help='Output PLY file or directory')
    parser.add_argument('--max_points', type=int, default=30000, help='Maximum number of points (default: 30000)')
    parser.add_argument('--downsample', type=str, default='uniform', choices=['uniform', 'voxel'],
                        help='Downsampling method: uniform (random) or voxel (structure-preserving)')

    args = parser.parse_args()

    # Check if input is file or directory
    if os.path.isfile(args.input):
        convert_pcd_to_ply(args.input, args.output, args.max_points, args.downsample)
    elif os.path.isdir(args.input):
        batch_convert(args.input, args.output, args.max_points, args.downsample)
    else:
        print(f"Error: {args.input} is not a valid file or directory")
