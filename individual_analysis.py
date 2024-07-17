import streamlit as st


def display_paginated_analyses(all_analyses, filter_option, items_per_page=10):
    filtered_analyses = [
        item for item in all_analyses
        if (filter_option == "Todas") or
           (filter_option == "Corretas" and item['color'] == 'green') or
           (filter_option == "Erradas" and item['color'] == 'red')
    ]

    total_pages = len(filtered_analyses) // items_per_page + \
        (1 if len(filtered_analyses) % items_per_page > 0 else 0)

    if 'page' not in st.session_state:
        st.session_state.page = 1

    def on_page_change():
        st.session_state.page = st.session_state.page_selectbox
        st.rerun()

    if total_pages > 0:
        page = st.selectbox("Página", options=range(1, total_pages + 1),
                            index=min(st.session_state.page -
                                      1, total_pages - 1),
                            key="page_selectbox",
                            on_change=on_page_change)

        start_idx = (st.session_state.page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(filtered_analyses))

        for item in filtered_analyses[start_idx:end_idx]:
            if item['color'] == 'green':
                st.success(
                    f"Nota Fiscal: {item['file_name']} ({item['status']})")
            else:
                st.error(
                    f"Nota Fiscal: {item['file_name']} ({item['status']})")

            with st.expander("Ver detalhes", expanded=False):
                st.markdown(item['analysis'])
                if item['color'] == 'green':
                    st.success(f"ESTA NOTA ESTÁ {item['status']}")
                else:
                    st.error(f"ESTA NOTA {item['status']}")

        st.write(
            f"Exibindo notas {start_idx + 1} a {end_idx} de {len(filtered_analyses)}")
    else:
        st.write("Nenhuma nota fiscal encontrada para os critérios selecionados.")


def individual_analysis():
    st.header("Análise Individual das Notas Fiscais")

    if not st.session_state.analyzed:
        st.warning(
            "Por favor, faça o upload e a análise das notas fiscais primeiro.")
        return

    filter_option = st.selectbox(
        "Filtrar notas fiscais:",
        options=["Todas", "Corretas", "Erradas"],
        index=0
    )

    display_paginated_analyses(st.session_state.all_analyses, filter_option)


# Chamada da função principal da página
individual_analysis()
