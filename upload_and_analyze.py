import streamlit as st
import time
from collections import Counter
import json
import xml.etree.ElementTree as ET


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
    
    **Número entre as tags <indPres> {ind_pres} </indPres>**\n
    
    **CLASSIFICAÇÃO DA OPERAÇÃO:** {classificacao}
    """

    # Implementação das novas regras
    cfop_list = ['6101', '6102', '6108', '6116']

    if cfop not in cfop_list:
        is_correct = True
        status = "CORRETA"
        color = "green"
    elif cfop in cfop_list and ind_pres != "1":
        is_correct = False
        status = "DEVE SER REVISADA"
        color = "red"
    else:
        is_correct = True
        status = "CORRETA"
        color = "green"

    return output, cfop, classificacao, is_correct, status, color


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
        analysis, cfop, classificacao, is_correct, status, color = analyze_nf(
            json_data)

        all_analyses.append({
            'file_name': file.name,
            'analysis': analysis,
            'is_correct': is_correct,
            'status': status,
            'color': color
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


def upload_and_analyze():
    st.header("Upload e Análise de Notas Fiscais")

    # Inicializar o session_state
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
            st.success(
                "Análise concluída! Você pode agora visualizar os resultados nas páginas 'Análise Individual' e 'Relatórios'.")

    if not uploaded_files:
        st.info(
            "Por favor, carregue os arquivos XML para iniciar a análise automatizada.")

    if st.session_state.analyzed:
        if st.button("Reiniciar Análise"):
            st.session_state.analyzed = False
            st.session_state.all_analyses = []
            st.session_state.cfop_counter = Counter()
            st.session_state.classificacao_counter = Counter()
            st.session_state.ind_pres_data = {}
            st.rerun()


# Chamada da função principal da página
upload_and_analyze()
