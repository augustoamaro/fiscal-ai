import streamlit as st

upload_and_analyze_page = st.Page(
    "upload_and_analyze.py", title="Upload e Análise", icon=":material/upload:")
individual_page = st.Page("individual_analysis.py",
                          title="Análise Individual", icon=":material/pageview:")
reports_page = st.Page("reports.py", title="Relatórios",
                       icon=":material/assessment:")

pg = st.navigation(
    [upload_and_analyze_page, individual_page, reports_page])
st.set_page_config(page_title="FiscAI", page_icon=":material/edit:")
pg.run()
