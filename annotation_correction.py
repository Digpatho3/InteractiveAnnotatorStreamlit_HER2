import numpy as np
from PIL import Image, ImageDraw

import matplotlib.pyplot as plt

from image_annotation import *
from pydrive_utils import *
from datetime import datetime, timedelta

todo_symbol = '(⬜️)'
toreview_symbol = '(👀)'
done_symbol = '(✅)'
discard_symbol = '(❌)'

# Folders
image_dir  = "./images"
ann_dir    = "./annotations"
report_dir = "./reports"

states = ['Sin anotar' , 
          'Revisar', 
          'OK', 
          'Descartado']
anns_todo_dir = 'anotaciones_a_hacer'
anns_toreview_dir = 'anotaciones_a_revisar'
anns_done_dir = 'anotaciones_ok'
anns_discarded_dir = 'anotaciones_descartadas'

path_to_json_key = "pydrive_credentials.json"

def setup_drive(session_state):
    try:
        drive = get_drive(path_to_json_key)
    except Exception:
        st.error("⚠️ Hubo un problema al inicializar la conexión con Google Drive. Notifica al administrador.")
        return -1

    # (optional) Get parent folder ID from secrets
    parent_folder_id = st.secrets["google_drive"].get("parent_folder_id", None)

    folder_dict, todo_dict, toreview_dict, done_dict, discarded_dict = \
        get_dicts(drive, anns_todo_dir, anns_toreview_dir, anns_done_dir, anns_discarded_dir, parent_folder_id)

    session_state['drive'] = drive
    session_state['todo_dict'] = todo_dict
    session_state['toreview_dict'] = toreview_dict
    session_state['done_dict'] = done_dict
    session_state['discarded_dict'] = discarded_dict
    session_state['folder_dict'] = folder_dict

    def add_metadata_to_samples(sample_dict, symbol):

        samples = []
        for sample_name, file_list in sample_dict.items():
            # Extract metadata from the first file in the list
            first_file = file_list[0]
            last_editor = first_file.get('lastModifyingUser', {}).get('displayName', 'Desconocido')
            if "@" in last_editor:  # If it's an email, take the part before '@'
                last_editor = last_editor.split("@")[0]
            last_modified_date = first_file.get('modifiedDate', 'Desconocida')
            
            # Adjust timezone to -3 if the date is not 'Desconocida'
            if last_modified_date != 'Desconocida':
                try:
                    # Parse the date and adjust timezone
                    gmt_date = datetime.strptime(last_modified_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                    adjusted_date = gmt_date - timedelta(hours=3)
                    last_modified_date = adjusted_date.strftime("%Y-%m-%d %H:%M:%S") + " (-03)"
                except ValueError:
                    # Handle unexpected date format
                    last_modified_date += " (-03)"
            
            samples.append(
                f"{sample_name} {symbol} (Editor: {last_editor}, Fecha: {last_modified_date})"
            )
        return samples

    # Store samples with metadata separately
    session_state['todo_samples'] = add_metadata_to_samples(todo_dict, todo_symbol)
    session_state['toreview_samples'] = add_metadata_to_samples(toreview_dict, toreview_symbol)
    session_state['done_samples'] = add_metadata_to_samples(done_dict, done_symbol)
    session_state['discarded_samples'] = add_metadata_to_samples(discarded_dict, discard_symbol)


    # Combine all sample names with their corresponding symbols
    sample_list = {}
    for sample_name in todo_dict.keys():
        sample_list[f"{sample_name} {todo_symbol}"] = sample_name
    for sample_name in toreview_dict.keys():
        sample_list[f"{sample_name} {toreview_symbol}"] = sample_name
    for sample_name in done_dict.keys():
        sample_list[f"{sample_name} {done_symbol}"] = sample_name
    for sample_name in discarded_dict.keys():
        sample_list[f"{sample_name} {discard_symbol}"] = sample_name

    session_state['display_samples'] = list(sample_list.keys())
    session_state['sample_names'] = list(sample_list.values())

    return 1


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
        discarded_dict = session_state['discarded_dict']

        try:
            if selected_sample in todo_dict.keys():
                img_path = get_gdrive_image_path(drive, todo_dict[selected_sample], image_dir, selected_sample)

            elif selected_sample in toreview_dict.keys():
                img_path = get_gdrive_image_path(drive, toreview_dict[selected_sample], image_dir, selected_sample)

            elif selected_sample in done_dict.keys():
                img_path = get_gdrive_image_path(drive, done_dict[selected_sample], image_dir, selected_sample)

            elif selected_sample in discarded_dict.keys():
                img_path = get_gdrive_image_path(drive, discarded_dict[selected_sample], image_dir, selected_sample)

        except Exception:
            st.error(f"⚠️ Hubo un problema al descargar la imagen para el sample '{selected_sample}'. Notifica al administrador.")
            return -1

    # Verify if the CSV file exists and is not empty
    if not os.path.exists(ann_file_path) or os.stat(ann_file_path).st_size == 0:
        drive = session_state['drive']
        todo_dict = session_state['todo_dict']
        toreview_dict = session_state['toreview_dict']
        done_dict = session_state['done_dict']
        discarded_dict = session_state['discarded_dict']

        try:
            if selected_sample in todo_dict.keys():
                # Create an empty CSV file locally
                with open(ann_file_path, 'w', encoding='utf-8') as ann_csv:
                    ann_csv.write("X,Y,Label\n")

            elif selected_sample in toreview_dict.keys():
                ann_file_path = get_gdrive_csv_path(drive, toreview_dict[selected_sample], ann_dir, selected_sample)

            elif selected_sample in done_dict.keys():
                ann_file_path = get_gdrive_csv_path(drive, done_dict[selected_sample], ann_dir, selected_sample)

            elif selected_sample in discarded_dict.keys():
                ann_file_path = get_gdrive_csv_path(drive, discarded_dict[selected_sample], ann_dir, selected_sample)

        except Exception:
            st.error(f"⚠️ Hubo un problema al descargar el archivo CSV para el sample '{selected_sample}'. Notifica al administrador.")
            return -1

    # Process the image and the CSV file
    image_file_name = selected_sample
    image = Image.open(img_path)
    height = image.size[1]
    width = image.size[0]
    scale = 1280 / width
    session_state['resized_image'] = image.resize((1280, int(scale * height)))
    session_state['height'] = int(scale * height)
    session_state['scale'] = scale

    try:
        with open(ann_file_path, 'r', encoding='utf-8') as ann_csv:
            annotations = ann_csv.read()
    except Exception:
        st.error(f"⚠️ Hubo un problema al leer el archivo CSV '{ann_file_path}'. Notifica al administrador.")
        return -1

    session_state['image_file_name'] = image_file_name
    session_state['img_path'] = img_path
    session_state['annotations'] = annotations

    all_points, all_labels = read_results_from_csv(ann_file_path)
    session_state['all_points'] = all_points
    session_state['all_labels'] = all_labels

    # This must be done last
    session_state['load_succesful'] = True
    return 1

def finish_annotation(session_state, selected_sample, target_dir):
    drive = session_state['drive']
    todo_dict = session_state['todo_dict']
    toreview_dict = session_state['toreview_dict']
    done_dict = session_state['done_dict']
    discarded_dict = session_state['discarded_dict']
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

    elif selected_sample in toreview_dict.keys() or \
         selected_sample in done_dict.keys() or \
         selected_sample in discarded_dict.keys():
        # Caso: La imagen proviene de toreview_dir, done_dir o discarded_dir
        if selected_sample in toreview_dict.keys():
            file_list = toreview_dict[selected_sample]
        elif selected_sample in done_dict.keys():
            file_list = done_dict[selected_sample]
        elif selected_sample in discarded_dict.keys():
            file_list = discarded_dict[selected_sample]

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
        if setup_drive(session_state) < 0:
            return
        

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
        # Hardcode the category to 'HER2/neu' and disable the selectbox
        category = 'HER2/neu'
        st.selectbox("Marcador:", [category], index=0, disabled=True)  # Disabled selectbox

        # Calculate the number of samples in each state
        todo_count = len(session_state.get('todo_samples', []))
        toreview_count = len(session_state.get('toreview_samples', []))
        done_count = len(session_state.get('done_samples', []))
        discarded_count = len(session_state.get('discarded_samples', []))

        # Update the state options to include the counts
        state_options = [
            f"{todo_symbol} {states[0]} ({todo_count})",
            f"{toreview_symbol} {states[1]} ({toreview_count})",
            f"{done_symbol} {states[2]} ({done_count})",
            f"{discard_symbol} {states[3]} ({discarded_count})"
        ]

        # Display the selectbox with the updated options
        enabled_dropdown = st.selectbox(
            "Estado:", 
            state_options, 
            index=0
        ).split(' ', 1)[1].rsplit(' ', 1)[0]  # Extract the state name without the count

        session_state['label'] = st.selectbox("Clase:", label_lists[category])
        session_state['action'] = st.selectbox("Acción:", actions)

    # Add a form to the sidebar for finalizing actions
    st.sidebar.header("Finalizar")
    with st.sidebar:
        with st.form("finalize_form", clear_on_submit=True):
            action = st.selectbox(
                "Selecciona una acción:",
                options=[
                    "---",
                    f"{toreview_symbol} Mandar a revisión",
                    f"{done_symbol} Finalizar anotación",
                    f"{discard_symbol} Descartar"
                ],
                index=0,
                help=(
                    "Selecciona una acción para la muestra actual:\n"
                    f"- {toreview_symbol} Mandar a revisión: Mueve la muestra a 'Revisar'.\n"
                    f"- {done_symbol} Finalizar anotación: Mueve la muestra a 'OK'.\n"
                    f"- {discard_symbol} Descartar: Mueve la muestra a 'Descartado'."
                )
            )

            # Every form must have a submit button
            submitted = st.form_submit_button("Confirmar acción")
            if submitted:
                if action == "---":
                    st.warning("Por favor, selecciona una acción válida antes de confirmar.")
                elif 'selected_sample' in session_state:
                    if action == f"{toreview_symbol} Mandar a revisión":
                        finish_annotation(session_state, session_state['selected_sample'], anns_toreview_dir)
                        st.success(f"Muestra '{session_state['selected_sample']}' enviada a revisión.")
                    elif action == f"{done_symbol} Finalizar anotación":
                        finish_annotation(session_state, session_state['selected_sample'], anns_done_dir)
                        st.success(f"Anotación finalizada para '{session_state['selected_sample']}'.")
                    elif action == f"{discard_symbol} Descartar":
                        finish_annotation(session_state, session_state['selected_sample'], anns_discarded_dir)
                        st.success(f"Muestra '{session_state['selected_sample']}' descartada.")
                    setup_drive(session_state)  # Update drive

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Get selected sample based on the chosen category
    selected_sample = None

    col1, col2, col3, col4 = st.columns([6, 2, 1, 1])

    sample_dict = {
        "Sin anotar": ("todo_samples", "Muestras sin anotar"),
        "Revisar": ("toreview_samples", "Muestras para revisar"),
        "OK": ("done_samples", "Muestras OK"),
        "Descartado": ("discarded_samples", "Muestras descartadas")
    }

    with col1:
        if enabled_dropdown in sample_dict:
            sample_key, label = sample_dict[enabled_dropdown]
            samples = session_state.get(sample_key, [])
            if samples:
                # Extract numeric parts of sample names for filtering
                sample_numbers = [
                    int(s.split('_')[-1].split(' ')[0]) for s in samples
                ]
                min_sample = min(sample_numbers)
                max_sample = max(sample_numbers)

                # Add sort options
                def sort_samples(samples, sort_by):
                    if sort_by == "00000 ➡️ 99999":
                        return sorted(samples, key=lambda x: x.rsplit(' ', 1)[0])
                    elif sort_by == "99999 ➡️ 00000":
                        return sorted(samples, key=lambda x: x.rsplit(' ', 1)[0], reverse=True)
                    elif sort_by == "Recientes primero":
                        return sorted(samples, key=lambda x: x.split("Fecha: ")[-1].strip(), reverse=True)
                    elif sort_by == "Antiguos primero":
                        return sorted(samples, key=lambda x: x.split("Fecha: ")[-1].strip())
                    elif sort_by == "Editor":
                        return sorted(samples, key=lambda x: x.split("Editor: ")[-1].split(",")[0].strip())
                    return samples    
                
                with col2:
                    sort_option = st.selectbox(
                        "Ordenamiento:",
                        options=["00000 ➡️ 99999",
                                "99999 ➡️ 00000", 
                                "Recientes primero", 
                                "Antiguos primero", 
                                "Editor"],
                        index=0,
                        help="Selecciona el criterio para ordenar las muestras:\n"
                            "- 00000 ➡️ 99999: Orden ascendente por número.\n"
                            "- 99999 ➡️ 00000: Orden descendente por número.\n"
                            "- Recientes primero: Orden por fecha de modificación más reciente.\n"
                            "- Antiguos primero: Orden por fecha de modificación más antigua.\n"
                            "- Editor: Orden alfabético por nombre del editor."
                    )

                # Add range filter
                with col3:
                    min_filter = st.number_input(
                        "N° mínimo", 
                        min_value=min_sample, 
                        max_value=max_sample, 
                        value=min_sample, 
                        step=1,
                        help="Establece el menor N° de muestra a mostrar."
                    )
                with col4:
                    max_filter = st.number_input(
                        "N° máximo", 
                        min_value=min_sample, 
                        max_value=max_sample, 
                        value=max_sample, 
                        step=1,
                        help="Establece el mayor N° de muestra a mostrar."
                    )

                # Filter samples based on range
                filtered_samples = [
                    s for s in samples 
                    if min_filter <= int(s.split('_')[-1].split(' ')[0]) <= max_filter
                ]

                sorted_samples = sort_samples(filtered_samples, sort_option)
                selected_sample_option = st.selectbox(
                    f"{label} ({len(sorted_samples)}):", 
                    sorted_samples
                )
                if selected_sample_option:
                    selected_sample = selected_sample_option.split(' ', 1)[0]
            else:
                st.warning(f"No hay {label.lower()} disponibles.")
        else:
            st.warning("Por favor, selecciona un estado válido.")
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
        if load_sample(session_state, selected_sample) < 0:
            return

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

        # colors for the current category
        colors = category_colors.get(category, None)

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
            colors=colors, # Pass the colors for the current category, if available
        )
        
        # Update points and labels in session state if any changes are made
        if new_labels is not None:

            # Incorporate the new labels
            all_points, all_labels = update_annotations(new_labels, all_points, all_labels, session_state)

            # Update results
            base_name = os.path.splitext(image_file_name)[0]
            update_results(session_state, all_points, all_labels, base_name)
            # update_ann_image(session_state, all_points, all_labels, image)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        st.subheader("Vista previa de las clases anotadas")

        # Crear el gráfico de vista previa
        fig, ax = plt.subplots(figsize=(10, 1))

        # Use custom colors if available
        if colors:
            label_colors = {label: color for label, color in zip(label_list, colors)}
        else:
            label_colors = get_colormap(label_list)
  
        for i, label in enumerate(label_list):
            ax.scatter(i, 0, color=label_colors[label], s=50)
            ax.text(i, -0.1, label, ha='center', va='top', fontsize=7)

        ax.set_xlim(-1, len(label_list))
        ax.set_ylim(-0.5, 0.5)
        ax.axis('off')
        st.pyplot(fig)

        # Display the annotation report generated in the session state
        st.text(session_state['report_data'])
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


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