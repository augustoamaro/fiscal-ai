import streamlit as st


def display_paginated_analyses(all_analyses, items_per_page=10):
    total_pages = len(all_analyses) // items_per_page + \
        (1 if len(all_analyses) % items_per_page > 0 else 0)

    if 'page' not in st.session_state:
        st.session_state.page = 1

    def on_page_change():
        st.session_state.page = st.session_state.page_selectbox
        st.rerun()

    page = st.selectbox("Página", options=range(1, total_pages + 1),
                        index=st.session_state.page - 1,
                        key="page_selectbox",
                        on_change=on_page_change)

    start_idx = (st.session_state.page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(all_analyses))

    for item in all_analyses[start_idx:end_idx]:
        if item['color'] == 'green':
            st.success(f"Nota Fiscal: {item['file_name']} ({item['status']})")
        else:
            st.error(f"Nota Fiscal: {item['file_name']} ({item['status']})")

        with st.expander("Ver detalhes", expanded=False):
            st.markdown(item['analysis'])
            if item['color'] == 'green':
                st.success(f"ESTA NOTA ESTÁ {item['status']}")
            else:
                st.error(f"ESTA NOTA {item['status']}")

    st.write(
        f"Exibindo notas {start_idx + 1} a {end_idx} de {len(all_analyses)}")


def individual_analysis():
    st.header("Análise Individual das Notas Fiscais")

    if not st.session_state.analyzed:
        st.warning(
            "Por favor, faça o upload e a análise das notas fiscais primeiro.")
        return

    display_paginated_analyses(st.session_state.all_analyses)


# Chamada da função principal da página
individual_analysis()
