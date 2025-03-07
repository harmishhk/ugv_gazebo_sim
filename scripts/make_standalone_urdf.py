#!/usr/bin/env python3

# This script is tested with following commands
# ./make_standalone_urdf.py scout_description scout_mini
# ./make_standalone_urdf.py scout_description scout_v2
# ./make_standalone_urdf.py ranger_mini_v3 ranger_mini
# ./make_standalone_urdf.py ranger_mini_v3 ranger_mini_gazebo
# ./make_standalone_urdf.py ranger_mini_v3 ranger_mini_isaac

import os
import shutil
import argparse
import xml.etree.ElementTree as ET
import subprocess
from ament_index_python.packages import get_package_share_directory
import tempfile

def generate_urdf_from_xacro(xacro_file, output_urdf):
    """Convert Xacro to URDF using ROS 2 xacro package."""
    try:
        subprocess.run(["ros2", "run", "xacro", "xacro", xacro_file, "-o", output_urdf], check=True)
        print(f"Converted Xacro to URDF: {output_urdf}")
        return output_urdf
    except subprocess.CalledProcessError:
        print("Error: Failed to convert Xacro to URDF.")
        return None

def find_or_generate_urdf(package_path, urdf_base_name, force_xacro=False):
    """Find URDF or generate it from Xacro if needed (or forced by --xacro flag)."""
    urdf_folder = os.path.join(package_path, "urdf")
    urdf_file = os.path.join(urdf_folder, f"{urdf_base_name}.urdf")
    xacro_file = os.path.join(urdf_folder, f"{urdf_base_name}.xacro")

    if force_xacro:
        if os.path.exists(xacro_file):
            print(f"Forced Xacro conversion: Using {xacro_file}")
            temp_urdf_file = os.path.join(tempfile.gettempdir(), f"{urdf_base_name}.urdf")
            return generate_urdf_from_xacro(xacro_file, temp_urdf_file)
        print(f"Error: Xacro file {xacro_file} not found but --xacro flag was used.")
        return None

    if os.path.exists(urdf_file):
        print(f"Found URDF: {urdf_file}")
        return urdf_file

    if os.path.exists(xacro_file):
        print(f"Xacro file found: {xacro_file}, converting to URDF...")
        temp_urdf_file = os.path.join(tempfile.gettempdir(), f"{urdf_base_name}.urdf")
        return generate_urdf_from_xacro(xacro_file, temp_urdf_file)

    print(f"Error: Neither {urdf_base_name}.urdf nor {urdf_base_name}.xacro found in {urdf_folder}.")
    return None

def make_standalone_urdf(package_name, urdf_base_name, destination_folder=None, force_xacro=False):
    try:
        package_path = get_package_share_directory(package_name)
    except ValueError:
        print(f"Error: Package '{package_name}' not found.")
        return

    urdf_source_path = find_or_generate_urdf(package_path, urdf_base_name, force_xacro)
    if urdf_source_path is None:
        return

    # If no destination is provided, create a folder with the URDF base name in the current directory
    if destination_folder is None:
        destination_folder = os.path.join(os.getcwd(), urdf_base_name)

    # Define paths
    mesh_source_dir = os.path.join(package_path, "meshes")
    os.makedirs(destination_folder, exist_ok=True)
    urdf_destination_path = os.path.join(destination_folder, f"{urdf_base_name}.urdf")
    meshes_destination_dir = os.path.join(destination_folder, "meshes")
    os.makedirs(meshes_destination_dir, exist_ok=True)

    # Copy URDF file
    shutil.copy(urdf_source_path, urdf_destination_path)

    # Parse URDF and copy meshes
    tree = ET.parse(urdf_destination_path)
    root = tree.getroot()

    for mesh in root.findall(".//mesh"):
        filename = mesh.get("filename")
        if filename:
            if filename.startswith("package://"):
                relative_path = filename.replace(f"package://{package_name}/", "")
            elif filename.startswith("file://"):
                relative_path = "meshes/" + filename.replace("file://", "").split("meshes/")[1]
            else:
                continue
            source_mesh_path = os.path.join(mesh_source_dir, os.path.relpath(relative_path, "meshes"))

            mesh_filename = os.path.basename(source_mesh_path)
            destination_mesh_path = os.path.join(meshes_destination_dir, mesh_filename)

            if os.path.exists(source_mesh_path):
                shutil.copy(source_mesh_path, destination_mesh_path)
                mesh.set("filename", f"meshes/{mesh_filename}")
            else:
                print(f"Warning: Mesh file {source_mesh_path} not found!")

    # Save the modified URDF
    tree.write(urdf_destination_path)
    print(f"URDF and meshes copied successfully to {destination_folder}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create standalone URDF and copy referenced meshes")
    parser.add_argument("package", type=str, help="ROS 2 package containing the URDF/Xacro and meshes")
    parser.add_argument("urdf", type=str, help="Base name of URDF/Xacro file (without extension)")
    parser.add_argument("outdir", type=str, nargs="?", default=None, help="Destination folder for the standalone URDF")
    parser.add_argument("--xacro", action="store_true", help="Always use Xacro to generate the URDF (even if URDF exists)")

    args = parser.parse_args()
    make_standalone_urdf(args.package, args.urdf, args.outdir, args.xacro)
