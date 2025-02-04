import streamlit as st

from ki67_annotator.ki67_annotation import image_ann as ki67_image_ann
from her2_annotator.her2_annotation import image_ann as her2_image_ann
from estr_annotator.estr_annotation import image_ann as estr_image_ann
from prog_annotator.prog_annotation import image_ann as prog_image_ann

app_list = ["Anotador KI67", "Anotador HER2", "Anotador Estrógeno", "Anotador Progesterona"]

# We want the wide mode to be set by default
st.set_page_config(page_title=None, page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)

def main():
    st.sidebar.header("Seleccionar aplicación")
    with st.sidebar:
        selected_app = st.selectbox("Aplicación:", app_list)
        st.session_state['Application'] = selected_app

    if selected_app == app_list[0]:
        image_dir = "./ki67_annotator/images"
        ann_dir = "./ki67_annotator/annotations"
        report_dir = "./ki67_annotator/reports"
        if 'ki67' not in st.session_state:
            st.session_state['ki67'] = {}
        ki67_image_ann(st.session_state['ki67'])
    elif selected_app == app_list[1]:
        image_dir = "./her2_annotator/images"
        ann_dir = "./her2_annotator/annotations"
        report_dir = "./her2_annotator/reports"
        if 'her2' not in st.session_state:
            st.session_state['her2'] = {}
        her2_image_ann(st.session_state['her2'])
    elif selected_app == app_list[2]:
        # image_dir = "./estr_annotator/images"
        # ann_dir = "./estr_annotator/annotations"
        # report_dir = "./estr_annotator/reports"
        # if 'estrogeno' not in st.session_state:
        #     st.session_state['estrogeno'] = {}
        # estr_image_ann(st.session_state['estrogeno'])
        st.warning("Esta aplicación aún no está disponible.")
    elif selected_app == app_list[3]:
        # image_dir = "./prog_annotator/images"
        # ann_dir = "./prog_annotator/annotations"
        # report_dir = "./prog_annotator/reports"
        # if 'progesterona' not in st.session_state:
        #     st.session_state['progesterona'] = {}
        # prog_image_ann(st.session_state['progesterona'])
        st.warning("Esta aplicación aún no está disponible.")

if __name__ == "__main__":
    main()
