import streamlit as st
import pandas as pd
import altair as alt
from collections import Counter


def display_report(cfop_counter, classificacao_counter, ind_pres_data):
    st.header("Relatório Final")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribuição de CFOP")

        cfop_df = pd.DataFrame.from_dict(
            cfop_counter, orient='index', columns=['count']).reset_index()
        cfop_df.columns = ['CFOP', 'Contagem']

        if not cfop_df.empty:
            cfop_df['CFOP'] = cfop_df['CFOP'].str[:4]
            grouped_cfop = cfop_df.groupby('CFOP')[
                'Contagem'].sum().reset_index()

            cfop_chart = alt.Chart(grouped_cfop).mark_bar().encode(
                x=alt.X('CFOP', title='CFOP'),
                y=alt.Y('Contagem', title='Número de Notas'),
                color='CFOP'
            ).properties(
                title='Distribuição de CFOP'
            )
            st.altair_chart(cfop_chart, use_container_width=True)
        else:
            st.write("Não há dados de CFOP para exibir.")

        st.write("Dados de CFOP:")

        def highlight_cfop(row):
            cfop = row['CFOP']
            highlight_cfops = ['6101', '6102', '6108', '6116']
            if cfop in highlight_cfops:
                ind_pres_values = ind_pres_data.get(cfop, [])
                if all(value == "1" for value in ind_pres_values):
                    # Verde para operações presenciais
                    return ['background-color: #059212' for _ in row]
                elif any(value != "1" for value in ind_pres_values):
                    # Vermelho para operações não presenciais
                    return ['background-color: #E4003A' for _ in row]
            # Verde para outros CFOPs
            return ['background-color: #059212' for _ in row]

        styled_df = grouped_cfop.style.apply(highlight_cfop, axis=1)
        st.dataframe(styled_df)

    with col2:
        st.subheader("Distribuição de Classificações")
        class_df = pd.DataFrame.from_dict(
            classificacao_counter, orient='index', columns=['count']).reset_index()
        class_df.columns = ['Classificação', 'Contagem']

        class_chart = alt.Chart(class_df).mark_arc().encode(
            theta='Contagem',
            color='Classificação',
            tooltip=['Classificação', 'Contagem']
        ).properties(
            title='Distribuição de Classificações de Operação'
        )
        st.altair_chart(class_chart, use_container_width=True)

        st.write("Dados de Classificações:")
        st.dataframe(class_df)


def reports():
    st.header("Relatórios")

    if not st.session_state.analyzed:
        st.warning(
            "Por favor, faça o upload e a análise das notas fiscais primeiro.")
        return

    display_report(st.session_state.cfop_counter,
                   st.session_state.classificacao_counter,
                   st.session_state.ind_pres_data)


reports()
