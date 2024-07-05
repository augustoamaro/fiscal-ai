import streamlit as st
import xml.etree.ElementTree as ET
import json
from collections import Counter
import base64
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
    **CFOP DA NOTA FISCAL:** {cfop}\n
    
    **Número entre as tags <indPres> e </indPres>:** {ind_pres}\n
    
    **CLASSIFICAÇÃO DA OPERAÇÃO:** {classificacao}
    """

    if ind_pres == "1":
        output += "\n**ESTA NOTA ESTÁ CORRETA**"

    return output, cfop, classificacao


def get_download_link(json_string, filename):
    b64 = base64.b64encode(json_string.encode()).decode()
    return f'<a href="data:application/json;base64,{b64}" download="{filename}">Baixar JSON</a>'


def display_report(cfop_counter, classificacao_counter):
    st.header("Relatório Final")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribuição de CFOP")
        cfop_df = pd.DataFrame.from_dict(
            cfop_counter, orient='index', columns=['count']).reset_index()
        cfop_df.columns = ['CFOP', 'Contagem']

        cfop_chart = alt.Chart(cfop_df).mark_bar().encode(
            x='CFOP',
            y='Contagem',
            color='CFOP'
        ).properties(
            title='Distribuição de CFOP'
        )
        st.altair_chart(cfop_chart, use_container_width=True)

        st.write("Dados de CFOP:")
        st.dataframe(cfop_df)

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
    progress_bar = st.progress(0)
    status_text = st.empty()

    st.header("Análise Individual das Notas Fiscais")

    for i, file in enumerate(uploaded_files):
        status_text.text(f"Processando: {file.name}")
        xml_content = file.read().decode('utf-8')
        json_content = xml_to_json(xml_content)
        json_data = json.loads(json_content)
        analysis, cfop, classificacao = analyze_nf(json_data)

        with st.expander(f"Nota Fiscal: {file.name}", expanded=False):
            st.markdown(analysis)

        cfop_counter[cfop] += 1
        classificacao_counter[classificacao] += 1

        progress = (i + 1) / len(uploaded_files)
        progress_bar.progress(progress)
        time.sleep(0.1)  # Simula um breve atraso para mostrar o progresso

    status_text.text("Processamento concluído!")
    time.sleep(1)
    status_text.empty()
    progress_bar.empty()

    return cfop_counter, classificacao_counter


def main():
    st.title("FiscAI - Assistente de Validação de Notas Fiscais")

    uploaded_files = st.file_uploader(
        "Carregue os arquivos XML das notas fiscais", accept_multiple_files=True, type=['xml'])

    if uploaded_files:
        if st.button("Iniciar Análise Automatizada"):
            with st.spinner("Iniciando análise..."):
                time.sleep(1)  # Simula um breve atraso inicial

            cfop_counter, classificacao_counter = process_files(uploaded_files)

            st.markdown("---")
            display_report(cfop_counter, classificacao_counter)

            st.success("Análise concluída com sucesso!")
    else:
        st.info(
            "Por favor, carregue os arquivos XML para iniciar a análise automatizada.")


if __name__ == "__main__":
    main()
