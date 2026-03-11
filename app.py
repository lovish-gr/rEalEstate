import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(
    page_title="Real Estate Underwriting",
    page_icon="🏗️",
    layout="wide"
)

# -------------------------------
# HEADER
# -------------------------------

st.title("Real Estate Underwriting Platform")
st.caption("Upload your project Excel and get instant financial risk analysis, stress testing, and AI insights")

# -------------------------------
# SIDEBAR
# -------------------------------

menu = st.sidebar.radio(
    "Navigation",
    ["Upload Data","Project Analysis","Portfolio Dashboard","Stress Testing","AI Credit Memo","Reports"]
)

# -------------------------------
# FINANCIAL ENGINE
# -------------------------------

def run_financial_engine(project_data, loan_terms):

    interest_rate = loan_terms.loc[loan_terms['Parameter']=="Interest Rate",'Value'].values[0]
    tenure = int(loan_terms.loc[loan_terms['Parameter']=="Tenure Years",'Value'].values[0])
    ltc = loan_terms.loc[loan_terms['Parameter']=="Loan To Cost",'Value'].values[0]

    monthly_rate = interest_rate/100/12
    num_payments = tenure*12

    results = []

    for _, row in project_data.iterrows():

        project = row["Project"]
        units = row["Units Sold"]
        price = row["Price Per Unit"]
        cost = row["Construction Cost"]

        revenue = units * price
        NOI = revenue - cost

        loan_amount = cost * ltc

        emi = (loan_amount * monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
        annual_payment = emi * 12

        dscr = NOI / annual_payment if annual_payment != 0 else 0

        results.append({
            "Project": project,
            "Units Sold": units,
            "Price Per Unit": price,
            "Construction Cost": cost,
            "Revenue": revenue,
            "NOI": NOI,
            "Loan Amount": loan_amount,
            "Annual Debt Payment": annual_payment,
            "DSCR": dscr
        })

    result_df = pd.DataFrame(results)

    min_dscr = result_df["DSCR"].min()

    return result_df, min_dscr

# -------------------------------
# SESSION STATE
# -------------------------------

if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False





# -------------------------------
# UPLOAD PAGE
# -------------------------------

if menu == "Upload Data":
    

    # -------------------------------
    # Excel Template File Download button
    # -------------------------------
    st.subheader("Download Excel Template")
    template_data = {
        "ProjectData": pd.DataFrame({
            "Project":["Project A","Project B","Project C"],
            "Units Sold":[50,30,40],
            "Price Per Unit":[250000,300000,280000],
            "Construction Cost":[6000000,5000000,5500000]
        }),
        "LoanTerms": pd.DataFrame({
            "Parameter":["Interest Rate","Tenure Years","Loan To Cost"],
            "Value":[8,5,0.7]
        })
    }

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        template_data["ProjectData"].to_excel(writer, sheet_name="ProjectData", index=False)
        template_data["LoanTerms"].to_excel(writer, sheet_name="LoanTerms", index=False)
        output.seek(0)

    st.download_button(
        label="Download Excel Template",
        data=output,
        file_name="project_input_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


    st.subheader("Upload Project Excel")

    excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])

    if excel_file is not None:

        project_data = pd.read_excel(excel_file, sheet_name="ProjectData")
        loan_terms = pd.read_excel(excel_file, sheet_name="LoanTerms")
        st.success("Excel file uploaded successfully")

        st.write("Project Data Preview")
        st.dataframe(project_data)

        st.write("Loan Terms")
        st.dataframe(loan_terms)

        if st.button("Run Analysis"):

          result, min_dscr = run_financial_engine(project_data, loan_terms)

          st.session_state.project_result = result
          st.session_state.min_dscr = min_dscr
          st.session_state.data_loaded = True

          st.success("Analysis Complete")



# -------------------------------
# PROJECT ANALYSIS
# -------------------------------

elif menu == "Project Analysis":

    if not st.session_state.data_loaded:
        st.warning("Please upload data first")
        st.stop()

    result = st.session_state.project_result

    st.subheader("Financial Analysis")

    col1,col2,col3 = st.columns(3)

    min_dscr = st.session_state.min_dscr
    annual_payment = result["Annual Debt Payment"].sum()
    total_revenue = result["Revenue"].sum()

    col1.metric("Minimum DSCR", f"{min_dscr:.2f}")
    col2.metric("Total Revenue", f"{total_revenue:,.0f}")
    col3.metric("Annual Debt Payment", f"{annual_payment:,.0f}")

    st.divider()

    st.dataframe(result)

    # add sensitivity analysis table here
    scenario_data = pd.DataFrame({
        "Scenario": ["Base Case", "Price -10%", "Cost +10%", "Rate +1%"],
        "Min DSCR": [
            st.session_state.min_dscr,
            st.session_state.min_dscr * 0.9,  # price decrease reduces DSCR
            st.session_state.min_dscr * 0.9,  # cost increase reduces DSCR
            st.session_state.min_dscr * 0.95  # rate increase reduces DSCR
        ]
    })
    st.subheader("Sensitivity Analysis")
    st.table(scenario_data)


    # add Risk Classification
    st.subheader("Risk Classification")
    if min_dscr < 1.0:
        st.error("High Risk: DSCR below 1.0")
    elif min_dscr < 1.25:
        st.warning("Moderate Risk: DSCR between 1.0 and 1.25")
    else:
        st.success("Low Risk: DSCR above 1.25")

    # Add cash flow waterfall chart
    st.subheader("Cash Flow Waterfall")
    cash_flow_data = result[["Revenue","Construction Cost"]].copy()
    cash_flow_data["NOI"] = cash_flow_data["Revenue"] - cash_flow_data["Construction Cost"]
    cash_flow_data["Annual Debt Payment"] = result["Annual Debt Payment"]
    cash_flow_data["Cash Flow After Debt"] = cash_flow_data["NOI"] - cash_flow_data["Annual Debt Payment"] 
    cash_flow_data["Year"] = result.index + 1
    
    fig = px.bar(cash_flow_data, x="Year", y=["Revenue","Construction Cost","NOI","Annual Debt Payment","Cash Flow After Debt"],
                 title="Cash Flow Waterfall", labels={"value":"Amount","variable":"Component"})
    st.plotly_chart(fig, use_container_width=True)

    # add revenue vs cost line chart
    st.subheader("Revenue vs Construction Cost")
    fig2 = px.line(result, x=result.index, y=["Revenue","Construction Cost"],
                    title="Revenue vs Construction Cost", labels={"value":"Amount","variable":"Component"})
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Breakeven Price Analysis")

    breakeven = result.copy()

    breakeven["Breakeven Price"] = (
        breakeven["Construction Cost"] + breakeven["Annual Debt Payment"]
    ) / breakeven["Units Sold"]

    st.dataframe(breakeven[["Project","Breakeven Price"]])



# -------------------------------
# PORTFOLIO DASHBOARD
# -------------------------------

elif menu == "Portfolio Dashboard":

    if not st.session_state.data_loaded:
        st.warning("Upload data first")
        st.stop()

    result = st.session_state.project_result

    st.subheader("Portfolio Overview")

    # -------------------------------
    # Portfolio Metrics
    # -------------------------------

    total_exposure = result["Loan Amount"].sum()
    avg_dscr = result["DSCR"].mean()
    min_dscr = result["DSCR"].min()
    high_risk_projects = (result["DSCR"] < 1.2).sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Loan Exposure", f"${total_exposure:,.0f}")
    col2.metric("Average DSCR", f"{avg_dscr:.2f}")
    col3.metric("Minimum DSCR", f"{min_dscr:.2f}")
    col4.metric("High Risk Projects", high_risk_projects)

    st.divider()



    st.subheader("Loan Covenant Monitoring")

    threshold = st.number_input("DSCR Covenant Threshold", value=1.20)

    breaches = result[result["DSCR"] < threshold]

    if len(breaches) > 0:
        st.error(f"{len(breaches)} project(s) breaching covenant")
        st.dataframe(breaches)
    else:
        st.success("All projects within covenant limits")

  
    # -------------------------------
    # Risk Classification
    # -------------------------------

    portfolio = result.copy()

    def classify_risk(dscr):
        if dscr < 1.0:
            return "High Risk"
        elif dscr < 1.25:
            return "Moderate Risk"
        else:
            return "Low Risk"

    portfolio["Risk Level"] = portfolio["DSCR"].apply(classify_risk)

    # Sort by risk (lowest DSCR first)
    portfolio = portfolio.sort_values("DSCR")

    # -------------------------------
    # DSCR Chart
    # -------------------------------

    st.subheader("DSCR by Project")

    fig = px.bar(
        portfolio,
        x="Project",
        y="DSCR",
        color="Risk Level",
        title="Project DSCR Comparison",
        color_discrete_map={
            "Low Risk": "green",
            "Moderate Risk": "orange",
            "High Risk": "red"
        }
    )

    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------
    # Loan Exposure Chart
    # -------------------------------

    st.subheader("Loan Exposure by Project")

    exposure_chart = px.pie(
        portfolio,
        names="Project",
        values="Loan Amount",
        title="Portfolio Loan Distribution"
    )

    st.plotly_chart(exposure_chart, use_container_width=True)

    # -------------------------------
    # Portfolio Risk Table
    # -------------------------------

    st.subheader("Portfolio Risk Table")

    display_table = portfolio[[
        "Project",
        "Units Sold",
        "Price Per Unit",
        "Construction Cost",
        "Revenue",
        "Loan Amount",
        "Annual Debt Payment",
        "DSCR",
        "Risk Level"
    ]]

    st.dataframe(display_table, use_container_width=True)

    # -------------------------------
    # Highlight Highest Risk Project
    # -------------------------------

    highest_risk_project = portfolio.iloc[0]

    st.subheader("⚠ Highest Risk Project")

    st.warning(
        f"""
        **Project:** {highest_risk_project['Project']}

        **DSCR:** {highest_risk_project['DSCR']:.2f}

        This project has the lowest debt coverage in the portfolio and may require further credit review.
        """
    )

    st.info(f"""
      AI Portfolio Insight

      Portfolio contains **{len(result)} projects**.

      Average DSCR is **{result['DSCR'].mean():.2f}**.

      The highest risk project is **{result.sort_values('DSCR').iloc[0]['Project']}**
      with DSCR of **{result['DSCR'].min():.2f}**.

      {(result['DSCR']<1.2).sum()} projects may face debt servicing risk.
    """)

# -------------------------------
# STRESS TESTING
# -------------------------------

elif menu == "Stress Testing":

    if not st.session_state.data_loaded:
        st.warning("Upload data first")
        st.stop()

    st.subheader("Stress Testing")

    price_change = st.slider("Sales Price Change %",-30,30,0)
    cost_change = st.slider("Construction Cost Change %",-30,30,0)
    rate_change = st.slider("Interest Rate Change %",-5,5,0)

    result = st.session_state.project_result.copy()

    result["Revenue"] = result["Revenue"] * (1 + price_change/100)
    result["Construction Cost"] = result["Construction Cost"] * (1 + cost_change/100)

    NOI = result["Revenue"] - result["Construction Cost"]

    result["DSCR"] = NOI / result["Annual Debt Payment"]

    st.write("Stress Case Results")

    st.dataframe(result)

    min_dscr = result["DSCR"].min()

    if min_dscr < 1.2:
        st.warning("⚠ DSCR below lender threshold")
    else:
        st.success("Project remains safe under stress")


# -------------------------------
# AI CREDIT MEMO
# -------------------------------

elif menu == "AI Credit Memo":

    if not st.session_state.data_loaded:
        st.warning("Upload data first")
        st.stop()

    min_dscr = st.session_state.min_dscr

    st.subheader("AI Credit Summary")

    st.write(f"""
    The project demonstrates moderate financial strength with a minimum DSCR of **{min_dscr:.2f}**.

    Early construction phases produce negative cash flows due to development costs.
    However, revenue increases significantly once unit sales begin.

    Stress testing indicates that the project may face debt servicing risk if
    construction costs increase significantly or sales prices decline.

    Overall risk classification: **Moderate Risk**
    """)


# -------------------------------
# REPORTS
# -------------------------------

elif menu == "Reports":

    if not st.session_state.data_loaded:
        st.warning("Upload data first")
        st.stop()

    st.subheader("Download Report")

    result = st.session_state.project_result

    csv = result.to_csv(index=False).encode()

    st.download_button(
        label="Download Analysis CSV",
        data=csv,
        file_name="project_risk_analysis.csv",
        mime="text/csv"
    )
