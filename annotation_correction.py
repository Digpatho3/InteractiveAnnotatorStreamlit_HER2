import numpy as np
from PIL import Image, ImageDraw

import matplotlib.pyplot as plt

from image_annotation import *
from pydrive_utils import *

todo_symbol = '(⬜️)'
toreview_symbol = '(👀)'
done_symbol = '(✅)'
discard_symbol = '(❌)'

# Folders
image_dir  = "./images"
ann_dir    = "./annotations"
report_dir = "./reports"

anns_todo_dir = 'anotaciones_a_hacer'
anns_toreview_dir = 'anotaciones_a_revisar'
anns_done_dir = 'anotaciones_ok'

parent_folder_id = '1Y423-t-9GesYP1RwRRmnBnQl8bRYEpAC' # Shared folder

biomarkers = ['Ki67', 'Estrógeno', 'Progesterona', 'HER2/neu']
label_lists = {
    'Ki67': ['Positivo', 'Negativo', 'No importante'],
    'Estrógeno': ['Positivo 3+', 'Positivo 2+', 'Positivo 1+', 'Negativo', 'No importante'],
    'Progesterona': ['Positivo 3+', 'Positivo 2+', 'Positivo 1+', 'Negativo', 'No importante'],
    'HER2/neu': ['Completa 3+', 'Completa 2+', 'Completa 1+', 'Incompleta 2+', 'Incompleta 1+', 'Ausente', 'No importa']
}
label_list = label_lists['HER2/neu']

path_to_json_key = "pydrive_credentials.json"

def setup_drive(session_state):
    drive = get_drive(path_to_json_key)

    folder_dict, todo_dict, toreview_dict, done_dict = \
        get_dicts(drive, anns_todo_dir, anns_toreview_dir, anns_done_dir, parent_folder_id)

    session_state['drive'] = drive
    session_state['todo_dict'] = todo_dict
    session_state['toreview_dict'] = toreview_dict
    session_state['done_dict'] = done_dict
    session_state['folder_dict'] = folder_dict

     # Store sample names separately
    session_state['todo_samples'] = [f"{sample_name} {todo_symbol}" for sample_name in todo_dict.keys()]
    session_state['toreview_samples'] = [f"{sample_name} {toreview_symbol}" for sample_name in toreview_dict.keys()]
    session_state['done_samples'] = [f"{sample_name} {done_symbol}" for sample_name in done_dict.keys()]

    # Combine all sample names with their corresponding symbols
    sample_list = {}
    for sample_name in todo_dict.keys():
        sample_list[f"{sample_name} {todo_symbol}"] = sample_name
    for sample_name in toreview_dict.keys():
        sample_list[f"{sample_name} {toreview_symbol}"] = sample_name
    for sample_name in done_dict.keys():
        sample_list[f"{sample_name} {done_symbol}"] = sample_name

    session_state['display_samples'] = list(sample_list.keys())
    session_state['sample_names'] = list(sample_list.values())


def load_sample(session_state, selected_sample):
    # Check if the selected sample is already downloaded
    img_path = None
    ann_file_path = f"{ann_dir}/{selected_sample}.csv"

    # Verify if the image is already downloaded
    for file in os.listdir(image_dir):
        if os.path.splitext(file)[0].strip() == selected_sample.strip():
            img_path = f"{image_dir}/{file}"
            break

    # Download the image if it is not present
    if img_path is None:
        drive = session_state['drive']
        todo_dict = session_state['todo_dict']
        toreview_dict = session_state['toreview_dict']
        done_dict = session_state['done_dict']

        if selected_sample in todo_dict.keys():
            img_path = get_gdrive_image_path(drive, todo_dict[selected_sample], image_dir, selected_sample)

        elif selected_sample in toreview_dict.keys():
            img_path = get_gdrive_image_path(drive, toreview_dict[selected_sample], image_dir, selected_sample)

        elif selected_sample in done_dict.keys():
            img_path = get_gdrive_image_path(drive, done_dict[selected_sample], image_dir, selected_sample)

    # Verify if the CSV file exists and is not empty
    if not os.path.exists(ann_file_path) or os.stat(ann_file_path).st_size == 0:
        drive = session_state['drive']
        todo_dict = session_state['todo_dict']
        toreview_dict = session_state['toreview_dict']
        done_dict = session_state['done_dict']

        if selected_sample in todo_dict.keys():
            # Create an empty CSV file locally
            with open(ann_file_path, 'w', encoding='utf-8') as ann_csv:
                ann_csv.write("X,Y,Label\n")

        elif selected_sample in toreview_dict.keys():
            ann_file_path = get_gdrive_csv_path(drive, toreview_dict[selected_sample], ann_dir, selected_sample)

        elif selected_sample in done_dict.keys():
            ann_file_path = get_gdrive_csv_path(drive, done_dict[selected_sample], ann_dir, selected_sample)

    # Process the image and the CSV file
    image_file_name = selected_sample
    image = Image.open(img_path)
    height = image.size[1]
    width = image.size[0]
    scale = 1280 / width
    session_state['resized_image'] = image.resize((1280, int(scale * height)))
    session_state['height'] = int(scale * height)
    session_state['scale'] = scale

    with open(ann_file_path, 'r', encoding='utf-8') as ann_csv:
        annotations = ann_csv.read()

    session_state['image_file_name'] = image_file_name
    session_state['img_path'] = img_path
    session_state['annotations'] = annotations

    all_points, all_labels = read_results_from_csv(ann_file_path)
    session_state['all_points'] = all_points
    session_state['all_labels'] = all_labels

    # This must be done last
    session_state['load_succesful'] = True

def finish_annotation(session_state, selected_sample, target_dir):
    drive = session_state['drive']
    todo_dict = session_state['todo_dict']
    toreview_dict = session_state['toreview_dict']
    done_dict = session_state['done_dict']
    folder_dict = session_state['folder_dict']

    target_folder_id = folder_dict[target_dir]['id']

    if selected_sample in todo_dict.keys():
        # Caso: La imagen proviene de todo_dir
        file_list = todo_dict[selected_sample]

        # Subir el archivo CSV local al directorio de destino
        csv_path = f"{ann_dir}/{selected_sample}.csv"
        upload_file_to_gdrive(drive, csv_path, target_folder_id)

        # Mover la imagen al directorio de destino
        for file in file_list:
            move_file(drive, file['id'], target_folder_id)

    elif selected_sample in toreview_dict.keys():
        # Caso: La imagen proviene de toreview_dir
        file_list = toreview_dict[selected_sample]

        # Actualizar el archivo CSV en su ubicación actual
        x_coords = []
        y_coords = []
        labels = []
        for point in session_state['all_points']:
            x_coords.append(point[0])
            y_coords.append(point[1])
            label_int = session_state['all_labels'][point]
            labels.append(label_list[label_int])

        update_gdrive_csv(drive, file_list, x_coords, y_coords, labels)

        # Mover el archivo CSV al directorio de destino
        for file in file_list:
            if file['title'].endswith('.csv'):
                move_file(drive, file['id'], target_folder_id)

        # Mover la imagen al directorio de destino
        for file in file_list:
            if not file['title'].endswith('.csv'):
                move_file(drive, file['id'], target_folder_id)

    elif selected_sample in done_dict.keys():
        # Caso: La imagen ya está en done_dir (no se mueve, pero se actualiza el CSV)
        file_list = done_dict[selected_sample]

        # Actualizar el archivo CSV en su ubicación actual
        x_coords = []
        y_coords = []
        labels = []
        for point in session_state['all_points']:
            x_coords.append(point[0])
            y_coords.append(point[1])
            label_int = session_state['all_labels'][point]
            labels.append(label_list[label_int])

        update_gdrive_csv(drive, file_list, x_coords, y_coords, labels)

def ann_correction(session_state):

    st.markdown(
        """
        ### ℹ️ Consejos de uso  
        - **Selección de puntos:** Haz clic y arrastra para dibujar un cuadro y seleccionar puntos.
        - **Eliminar puntos:** Presionar 'retroceso' permite eliminar los puntos seleccionados.
        - **Cambiar etiqueta:** Presionar 'shift' cambia la clase del punto seleccionado.  
        - **Mover imagen horizontalmente:** Usa las flechas del teclado para moverte a través de la imagen.
        """,
        unsafe_allow_html=True
    )

    if 'drive' not in session_state:
        
        json_contents = st.secrets["service_account"]["credentials"]
        json_contents = json.loads(json_contents)

        with open(path_to_json_key, "w") as json_file:
            json.dump(json_contents, json_file, indent=4)  # Pretty formatting

        init_session(session_state)
        setup_drive(session_state)

    st.sidebar.header("Visualización")
    with st.sidebar:
        point_count = len(session_state['all_points']) if 'all_points' in session_state else 0
        point_vis = st.checkbox(
            f"Mostrar puntos ({point_count})", 
            value=True, 
            help="Activa o desactiva la visualización de los puntos en la imagen."
            )
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
            enabled_dropdown = st.selectbox(
                "Estado:",
                ["Sin anotar", "Revisar", "OK"],
                index=0
                )
        with col2:
            category = st.selectbox("Marcador:", categories, index=categories.index('HER2/neu')) # hardcoded
            session_state['label'] = st.selectbox("Clase:", label_lists[category])

    # Add a button to the sidebar
    st.sidebar.header("Finalizar")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Finalizar anotación"):
            if 'selected_sample' in session_state:
                finish_annotation(session_state, session_state['selected_sample'], anns_done_dir)
                setup_drive(session_state)  # Update drive
    with col2:
        if st.button("Mandar a revisión"):
            if 'selected_sample' in session_state:
                finish_annotation(session_state, session_state['selected_sample'], anns_toreview_dir)
                setup_drive(session_state)  # Update drive

    # Get selected sample based on the chosen category
    selected_sample = None
    if enabled_dropdown == "Sin anotar":
        if session_state['todo_samples']:
            selected_sample_option = st.selectbox(
                f"Muestras sin anotar ({len(session_state['todo_samples'])}):", 
                session_state['todo_samples']
            )
            if selected_sample_option:
                selected_sample = selected_sample_option.rsplit(' ', 1)[0]
        else:
            st.warning("No hay muestras sin anotar disponibles.")
    elif enabled_dropdown == "Revisar":
        if session_state['toreview_samples']:
            selected_sample_option = st.selectbox(
                f"Muestras para revisar ({len(session_state['toreview_samples'])}):", 
                session_state['toreview_samples']
            )
            if selected_sample_option:
                selected_sample = selected_sample_option.rsplit(' ', 1)[0]
        else:
            st.warning("No hay muestras para revisar disponibles.")
    elif enabled_dropdown == "OK":
        if session_state['done_samples']:
            selected_sample_option = st.selectbox(
                f"Muestras OK ({len(session_state['done_samples'])}):", 
                session_state['done_samples']
            )
            if selected_sample_option:
                selected_sample = selected_sample_option.rsplit(' ', 1)[0]
        else:
            st.warning("No hay muestras OK disponibles.")

    # Clear previously loaded sample if no new sample is selected
    if not selected_sample:
        session_state['selected_sample'] = None
        session_state['load_succesful'] = False
        return

    # Ensure the dropdown for selecting samples remains visible
    if selected_sample is None:
        st.warning("Por favor, selecciona una muestra del desplegable habilitado.")
        selected_sample = session_state.get('selected_sample', None)

    # We check for changes on the selected sample
    if 'selected_sample' not in session_state or \
        session_state['selected_sample'] != selected_sample:

        # We update the selected sample and trigger
        # the loading of the sample 
        session_state['load_succesful'] = False
        session_state['selected_sample'] = selected_sample

    # We check if the last load was succesful
    if 'load_succesful' not in session_state or \
        session_state['load_succesful'] != True:
        load_sample(session_state, selected_sample)

    if 'image_file_name' in session_state:
        image_file_name  = session_state['image_file_name']
        img_path = session_state['img_path']

    else:
        image_file_name = None

    if image_file_name is not None:

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
            csv_file_name = f"{ann_dir}/{base_name}.csv"
            all_points, all_labels = read_results_from_csv(csv_file_name)
            recover_session(session_state, all_points, all_labels, base_name)

            mode  = 'Transform'

        update_patch_data(session_state, all_points, all_labels)

        # Use pointdet to annotate the image
        new_labels = pointdet(
            image=session_state['resized_image'],
            label_list=label_list,
            points=session_state['points'],
            labels=session_state['labels'],
            width = 1280,
            height = session_state['height'],
            manual_scale = session_state['scale'],
            use_space=True,
            key=img_path,
            mode = mode,
            label = session_state['label'],
            point_width=5*point_vis,
            zoom=zoom,
        )

        st.subheader("Vista previa de las clases anotadas")
        fig, ax = plt.subplots(figsize=(10, 1))

        label_colors = get_colormap(label_list)

        for i, label in enumerate(label_list):
            ax.scatter(i, 0, color=label_colors[label], s=50)
            ax.text(i, -0.1, label, ha='center', va='top', fontsize=7)

        ax.set_xlim(-1, len(label_list))
        ax.set_ylim(-0.5, 0.5)
        ax.axis('off') 
        st.pyplot(fig)
        
        # Update points and labels in session state if any changes are made
        if new_labels is not None:

            # Incorporate the new labels
            all_points, all_labels = update_annotations(new_labels, all_points, all_labels, session_state)

            # Update results
            base_name = os.path.splitext(image_file_name)[0]
            update_results(session_state, all_points, all_labels, base_name)
            # update_ann_image(session_state, all_points, all_labels, image)


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

            # # **3rd Download Button** - Annotated Image
            # st.download_button(
            #     label="Descargar imagen anotada (png)",
            #     data=session_state['ann_image'],
            #     file_name=f'{image_name}_annotated.png',
            #     mime='image/png'
            # )