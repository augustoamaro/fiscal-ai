import streamlit as st
import xml.etree.ElementTree as ET
import json
from collections import Counter
import pandas as pd
import altair as alt
import time


def remove_namespace(tag):
    return tag.split('}')[-1] if '}' in tag else tag


def xml_to_json(xml_string):
    def _elem_to_dict(elem):
        result = {}
        for child in elem:
            child_tag = remove_namespace(child.tag)
            child_dict = _elem_to_dict(child)
            if child_tag in result:
                if isinstance(result[child_tag], list):
                    result[child_tag].append(child_dict)
                else:
                    result[child_tag] = [result[child_tag], child_dict]
            else:
                result[child_tag] = child_dict

        if elem.attrib:
            result["@attributes"] = {remove_namespace(
                k): v for k, v in elem.attrib.items()}

        if elem.text and elem.text.strip():
            if not result:
                result = elem.text.strip()
            else:
                result["#text"] = elem.text.strip()

        if not result and not elem.text:
            return None
        elif isinstance(result, str):
            return result
        elif not result:
            return None

        return result

    root = ET.fromstring(xml_string)
    return json.dumps(_elem_to_dict(root), indent=2, ensure_ascii=False)


def extract_value(json_data, key):
    def _extract(obj, key):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == key:
                    return v
                if isinstance(v, (dict, list)):
                    result = _extract(v, key)
                    if result is not None:
                        return result
        elif isinstance(obj, list):
            for item in obj:
                result = _extract(item, key)
                if result is not None:
                    return result
        return None

    value = _extract(json_data, key)
    return value if value is not None else "Não encontrado"


def analyze_nf(json_data):
    nf_id = extract_value(json_data, "Id")
    cnpj = extract_value(json_data, "CNPJ")
    nNF = extract_value(json_data, "nNF")
    serie = extract_value(json_data, "serie")
    cfop = extract_value(json_data, "CFOP")
    ind_pres = extract_value(json_data, "indPres")

    classificacao_operacao = {
        "0": "Não se aplica (ex: Nota Fiscal complementar ou de ajuste)",
        "1": "Operação presencial",
        "2": "Operação não presencial, pela Internet",
        "3": "Operação não presencial, Teleatendimento",
        "4": "NFC-e em operação com entrega a domicílio",
        "5": "Operação presencial, fora do estabelecimento",
        "9": "Operação não presencial, outros"
    }

    classificacao = classificacao_operacao.get(
        ind_pres, "Classificação não identificada")

    output = f"""
    **ID DA NOTA:** {nf_id}\n
    **CNPJ DA NOTA:** {cnpj}\n
    **NÚMERO DA NOTA FISCAL:** {nNF}\n
    **SÉRIE DA NOTA FISCAL:** {serie}\n
    **CFOP DA NOTA FISCAL:** {cfop}\n\n
    
    **Número entre as tags <indPres> {ind_pres} </indPres>:**\n
    
    **CLASSIFICAÇÃO DA OPERAÇÃO:** {classificacao}
    """

    is_correct = ind_pres == "1"

    return output, cfop, classificacao, is_correct


def display_report(cfop_counter, classificacao_counter, ind_pres_data):
    st.header("Relatório Final")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribuição de CFOP")

        filtered_cfop = {k: v for k, v in cfop_counter.items()
                         if k.startswith(('5', '6'))}
        cfop_df = pd.DataFrame.from_dict(
            filtered_cfop, orient='index', columns=['count']).reset_index()
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
                title='Distribuição de CFOP (5xxx e 6xxx)'
            )
            st.altair_chart(cfop_chart, use_container_width=True)
        else:
            st.write("Não há dados de CFOP começando com 5 ou 6 para exibir.")

        st.write("Dados de CFOP (5xxx e 6xxx):")

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
            return [''] * len(row)

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


def process_files(uploaded_files):
    cfop_counter = Counter()
    classificacao_counter = Counter()
    ind_pres_data = {}
    progress_bar = st.progress(0)
    status_text = st.empty()

    st.header("Análise Individual das Notas Fiscais")

    all_analyses = []

    for i, file in enumerate(uploaded_files):
        status_text.text(f"Processando: {file.name}")
        xml_content = file.read().decode('utf-8')
        json_content = xml_to_json(xml_content)
        json_data = json.loads(json_content)
        analysis, cfop, classificacao, is_correct = analyze_nf(json_data)

        all_analyses.append({
            'file_name': file.name,
            'analysis': analysis,
            'is_correct': is_correct
        })

        cfop_counter[cfop] += 1
        classificacao_counter[classificacao] += 1

        ind_pres = extract_value(json_data, "indPres")
        if cfop not in ind_pres_data:
            ind_pres_data[cfop] = []
        ind_pres_data[cfop].append(ind_pres)

        progress = (i + 1) / len(uploaded_files)
        progress_bar.progress(progress)
        time.sleep(0.1)

    status_text.text("Processamento concluído!")
    time.sleep(1)
    status_text.empty()
    progress_bar.empty()

    return cfop_counter, classificacao_counter, all_analyses, ind_pres_data


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
        if item['is_correct']:
            st.success(f"Nota Fiscal: {item['file_name']} (CORRETA)")
        else:
            st.error(f"Nota Fiscal: {item['file_name']} (INCORRETA)")

        with st.expander("Ver detalhes", expanded=False):
            st.markdown(item['analysis'])
            if item['is_correct']:
                st.success("ESTA NOTA ESTÁ CORRETA")
            else:
                st.error("ESTA NOTA NÃO ESTÁ CORRETA")

    st.write(
        f"Exibindo notas {start_idx + 1} a {end_idx} de {len(all_analyses)}")


def main():
    st.title("FiscAI - Assistente de Validação de Notas Fiscais")

    if 'analyzed' not in st.session_state:
        st.session_state.analyzed = False
    if 'all_analyses' not in st.session_state:
        st.session_state.all_analyses = []
    if 'cfop_counter' not in st.session_state:
        st.session_state.cfop_counter = Counter()
    if 'classificacao_counter' not in st.session_state:
        st.session_state.classificacao_counter = Counter()
    if 'ind_pres_data' not in st.session_state:
        st.session_state.ind_pres_data = {}

    uploaded_files = st.file_uploader(
        "Carregue os arquivos XML das notas fiscais", accept_multiple_files=True, type=['xml'])

    if uploaded_files and not st.session_state.analyzed:
        if st.button("Iniciar Análise Automatizada"):
            with st.spinner("Iniciando análise..."):
                time.sleep(1)

            st.session_state.cfop_counter, st.session_state.classificacao_counter, st.session_state.all_analyses, st.session_state.ind_pres_data = process_files(
                uploaded_files)
            st.session_state.analyzed = True

    if st.session_state.analyzed:
        st.markdown("---")
        display_paginated_analyses(st.session_state.all_analyses)

        st.markdown("---")
        display_report(st.session_state.cfop_counter,
                       st.session_state.classificacao_counter,
                       st.session_state.ind_pres_data)

        if st.button("Reiniciar Análise"):
            st.session_state.analyzed = False
            st.session_state.all_analyses = []
            st.session_state.cfop_counter = Counter()
            st.session_state.classificacao_counter = Counter()
            st.session_state.ind_pres_data = {}
            st.rerun()
    elif not uploaded_files:
        st.info(
            "Por favor, carregue os arquivos XML para iniciar a análise automatizada.")


if __name__ == "__main__":
    main()
