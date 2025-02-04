import streamlit as st
from streamlit_image_annotation import pointdet
import io
import csv
from PIL import Image
from PIL import Image, ImageDraw
import numpy as np
import pandas as pd
import os
from pathlib import Path

# Folders
MODULE_DIR = Path(__file__).parent.absolute()
DATA_DIR = MODULE_DIR / "data"
IMAGE_DIR = DATA_DIR / "images"
ANN_DIR = DATA_DIR / "annotations"
REPORT_DIR = DATA_DIR / "reports"
LOG_FILE = DATA_DIR / "latest_session.log"

# Create all directories
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
ANN_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Define label list
label_list = ['Completa 3+', 'Completa 2+', 'Completa 1+', 'Incompleta 2+', 'Incompleta 1+', 'Ausente']
actions = ['Agregar', 'Borrar']

def init_session(session_state):
    session_state.update({
        'all_points': set(),
        'all_labels': {},
        'points': [],
        'labels': [],
        'csv_data': b"",  # Inicializar como bytes vacíos
        'report_data': b"",
        'ann_image': b""
    })

def update_patch_data(session_state, all_points, all_labels):

    points = list(all_points)
    labels = [all_labels[point] for point in all_points]

    session_state['points'] = points
    session_state['labels'] = labels


def update_results(session_state, all_points, all_labels, file_name):

    points = list(all_points)
    labels = [all_labels[point] for point in all_points]

    # Create CSV content
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    csv_writer.writerow(["X", "Y", "Label"])
    for point, label in zip(points, labels):
        csv_writer.writerow([point[0], point[1], label_list[label]])

    # Convert CSV buffer to downloadable file
    csv_data = csv_buffer.getvalue().encode('utf-8')

    # Save CSV data to file
    csv_data = csv_buffer.getvalue()
    csv_filename = f"{ANN_DIR}/{file_name}.csv"
    Path(ANN_DIR).mkdir(parents=True, exist_ok=True)
    with open(csv_filename, "w", encoding="utf-8") as csv_file:
        csv_file.write(csv_data)

    # **Generate the Annotation Report**
    num_positive = labels.count(0)
    num_negative = labels.count(1)

    total = num_positive + num_negative

    if total==0:
        total = -1

    report_content = f"""
    Reporte de anotación
    ==================
    Nombre de la imagen: {file_name}
    Número de puntos positivos: {num_positive} - Porcentaje: {100*num_positive/total}%
    Número de puntos negativos: {num_negative} - Porcentaje: {100*num_negative/total}%
    Cantidad total de elementos {total}
    """

    # Create file-like object to download the report
    report_buffer = io.StringIO()
    report_buffer.write(report_content)
    report_data = report_buffer.getvalue()

    # Save report to file
    report_filename = f"{REPORT_DIR}/{file_name}.txt"
    Path(REPORT_DIR).mkdir(parents=True, exist_ok=True)
    with open(report_filename, "w", encoding="utf-8") as report_file:
        report_file.write(report_content)

    session_state['csv_data'] = csv_data
    session_state['report_data'] = report_data


def update_annotations(new_labels, all_points, all_labels, session_state):

    patch_points = []

    # Add new points
    for v in new_labels:
        x, y = v['point']

        x = int(x)
        y = int(y)

        label_id = v['label_id']
        patch_points.append([x, y])

        point_tuple = (x, y)

        if point_tuple not in all_points:
            all_points.add(point_tuple)
            all_labels[point_tuple] = label_id  # Store the label for this point

    # Remove points
    removed_points = []
    for global_point in all_points:
        x, y = global_point

        remove_flag = True

        for patch_point in patch_points:

            x_patch, y_patch = patch_point

            nequal_flag = not ( (x == x_patch) and (y == y_patch) )

            remove_flag = remove_flag and nequal_flag

        if remove_flag:
            removed_points.append(global_point)


    for removed_point in removed_points:
        all_points.remove(removed_point)
        del all_labels[removed_point]  # Remove the corresponding label

    session_state['all_points'] = all_points
    session_state['all_labels'] = all_labels

    return all_points, all_labels


def update_ann_image(session_state, all_points, all_labels, image):
    """
    Overlays points on the image with colors corresponding to their labels 
    and stores the result in the session state for display and download.

    Args:
        session_state: dict containing `all_points` and `all_labels`.
            - `all_points`: List of tuples representing points (x, y).
            - `all_labels`: Dictionary mapping points to labels.
        image: PIL.Image object representing the base image.
    """

    # Define colors for each label
    label_colors = {
        # Completa (RGB puro para máximo contraste)
        0: (255, 59, 59),    # Rojo quirúrgico
        1: (255, 178, 0),    # Ámbar
        2: (255, 237, 0),    # Amarillo fluor
        
        # Incompleta (Tonos fríos no presentes en tinciones H&E)
        3: (0, 100, 255),    # Azul real
        4: (0, 206, 255),    # Cian
        
        # Ausente (Gris corregido gamma)
        5: (128, 128, 128)   # Gris neutral (gamma 2.2)
        
        # Add more labels and their colors as needed
    }

    # Create a drawable image
    ann_image = image.copy()
    draw = ImageDraw.Draw(ann_image)

    # Draw each point with the corresponding color
    point_radius = 7.5  # Radius of each point
    for point in all_points:
        x, y = point
        label = all_labels.get(point, "default")  # Get the label for the point
        color = label_colors.get(label, (255, 255, 255))  # Default to white if label not found

        # Draw the point as a filled circle
        draw.ellipse(
            [(x - point_radius, y - point_radius), (x + point_radius, y + point_radius)],
            outline=color,
            width=5,
        )

    # Convert the annotated image to a downloadable JPEG format
    image_buffer = io.BytesIO()
    ann_image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    # Store the annotated image
    session_state['ann_image'] = image_buffer


def recover_session(session_state, all_points, all_labels, image, file_name):

    session_state['all_points'] = all_points 
    session_state['all_labels'] = all_labels 

    update_patch_data(session_state, all_points, all_labels)
    update_results(session_state, all_points, all_labels, file_name)
    update_ann_image(session_state, all_points, all_labels, image)


def check_latest_session_log(log_path=LOG_FILE):
    try:
        with open(log_path, 'r', encoding='utf-8') as file:
            contents = file.read()

        return contents

    except FileNotFoundError:
        return "NoImage"
    except Exception as e:
        return "NoImage"


def store_latest_session_log(file_name, log_path=LOG_FILE):
    try:
        with open(log_path, 'w', encoding='utf-8') as file:
            file.write(file_name)
    except Exception as e:
        print(f"An error occurred: {e}")


def check_files(image_file_name, folder_path):
    """
    Checks if a file (without its extension) exists in the specified folder.

    Args:
        image_file_name (str): The name of the file to check (without extension).
        folder_path (str): The path of the folder to search in. Default is "/path/to/your/folder".

    Returns:
        bool: True if the file (ignoring extensions) exists, False otherwise.
    """
    # Normalize the file name to search (strip extension if any)
    image_file_base = os.path.splitext(image_file_name)[0]

    # List all files in the folder without their extensions
    file_names_in_folder = [
        os.path.splitext(f)[0]
        for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
    ]

    # Check if the file exists (case-sensitive)
    return image_file_base in file_names_in_folder


def read_results_from_csv(csv_filename):
    """
    Reads the contents of a CSV file created by the `update_results` function
    and extracts all_points and all_labels.

    Args:
        csv_filename (str): Path to the CSV file to read.

    Returns:
        tuple: A tuple containing:
            - all_points (list of tuples): List of points [(x1, y1), (x2, y2), ...].
            - all_labels (list): List of labels corresponding to each point.
    """
    all_points = set()
    all_labels = {}

    try:
        with open(csv_filename, mode="r", encoding="utf-8") as csv_file:
            csv_reader = csv.DictReader(csv_file)  # Read CSV with headers
            for row in csv_reader:
                # Extract X, Y, and Label, and reconstruct all_points and all_labels
                x = int(row["X"])
                y = int(row["Y"])
                label_id = label_list.index(row["Label"])
                point_tuple = (x, y)

                all_points.add(point_tuple)
                all_labels[point_tuple] = label_id  # Store the label for this point

    except FileNotFoundError:
        print(f"Error: File '{csv_filename}' not found.")
    except Exception as e:
        print(f"Error reading the file: {e}")
    
    return all_points, all_labels


def get_image():

    image = None     
    image_file_name = None
    img_path = None

    # Image upload
    uploaded_file = st.file_uploader("Subir imagen ", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image_file_name = uploaded_file.name
        image = Image.open(uploaded_file)
        img_path = f"{IMAGE_DIR}/{image_file_name}"

    # No image was uploaded - We use the latest one from a previous session
    else: 
        # Check latest image
        latest_image = check_latest_session_log()
        result = check_files(latest_image, IMAGE_DIR)

        if result:
            # Recover the latest image
            image_file_name = latest_image
            image_path = f"{IMAGE_DIR}/{latest_image}"
            if os.path.exists(image_path):
                image = Image.open(image_path)
                img_path = image_path
            else:
                st.error(f"Error: File '{image_path}' not found.")
        else:
            st.error("No image found in the latest session log.")

    return image, image_file_name, img_path    


def handle_new_image(session_state, image, image_file_name, img_path):

    # We update the name of the current image
    session_state['image_file_name'] = image_file_name

    # We check if the image was previously annotated
    result = check_files(image_file_name, IMAGE_DIR)

    if result: # Recover previous annotations
        base_name = os.path.splitext(image_file_name)[0]
        csv_file_name = f"{ANN_DIR}/{base_name}.csv"
        all_points, all_labels = read_results_from_csv(csv_file_name)
        recover_session(session_state, all_points, all_labels, image, base_name)

    else: # We store a backup of the image
        Path(img_path).parent.mkdir(parents=True, exist_ok=True)
        image.save(img_path)
        init_session(session_state)

    # We log the name of the image for session backups
    store_latest_session_log(image_file_name)


def image_ann(session_state):

    st.sidebar.header("Seleccionar zoom")
    with st.sidebar:
        zoom = st.number_input(
            "Zoom", 
            min_value=1, 
            max_value=4, 
            value=1, 
            step=1
        )            

    # Sidebar content
    st.sidebar.header("Anotación de imágenes")
    with st.sidebar:
        col1, col2 = st.columns([2, 2])
        with col1:
            session_state['action'] = st.selectbox("Acción:", actions)

        with col2:
            session_state['label'] = st.selectbox("Clase:", label_list)


    image, image_file_name, img_path = get_image()

    if image_file_name is not None:

        # Check if a new image is uploaded
        if 'image_file_name' not in session_state or session_state['image_file_name'] != image_file_name:
            handle_new_image(session_state, image, image_file_name, img_path)

        try:
            all_points = session_state['all_points']
            all_labels = session_state['all_labels']

            # Translate the selected action
            action = session_state['action']
            if action == actions[1]:
                mode = 'Del'
            else:
                mode = 'Transform'


        # User got disconnected - We recover the previous session
        except KeyError:
            base_name = os.path.splitext(image_file_name)[0]
            csv_file_name = f"{ANN_DIR}/{base_name}.csv"
            all_points, all_labels = read_results_from_csv(csv_file_name)
            recover_session(session_state, all_points, all_labels, image, base_name)

            mode  = 'Transform'


        update_patch_data(session_state, all_points, all_labels)
                    
        # Use pointdet to annotate the image
        new_labels = pointdet(
            image_path=img_path,
            label_list=label_list,
            points=session_state['points'],
            labels=session_state['labels'],
            width = image.size[0],
            height = image.size[1],
            use_space=True,
            key=img_path,
            mode = mode,
            label = session_state['label'],
            point_width=5,
            zoom=zoom,
        )
        
        # Update points and labels in session state if any changes are made
        if new_labels is not None:

            # Incorporate the new labels
            all_points, all_labels = update_annotations(new_labels, all_points, all_labels, session_state)

            # Update results
            base_name = os.path.splitext(image_file_name)[0]
            update_results(session_state, all_points, all_labels, base_name)
            update_ann_image(session_state, all_points, all_labels, image)



    # Download results
    if 'image_file_name' in session_state:
        st.sidebar.header("Resultados")
        with st.sidebar:
            image_name = os.path.splitext(session_state['image_file_name'])[0]
            # **1st Download Button** - CSV Annotations
            st.download_button(
                label="Descargar anotaciones (CSV)",
                data=session_state['csv_data'],
                file_name=f"{image_name}.csv",
                mime="text/csv"
            )

            # **2nd Download Button** - Annotation Report
            st.download_button(
                label="Descargar reporte (txt)",
                data=session_state['report_data'],
                file_name=f'{image_name}.txt',
                mime='text/plain'
            )

            # **3rd Download Button** - Annotated Image
            st.download_button(
                label="Descargar imagen anotada (png)",
                data=session_state['ann_image'],
                file_name=f'{image_name}_annotated.png',
                mime='image/png'
            )