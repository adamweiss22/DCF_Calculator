import pandas as pd
import sys
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

try:
    import yfinance as yf
except ImportError:
    print("Error: The 'yfinance' package is not installed.")
    print("Please install it by running: pip install yfinance")
    sys.exit(1)

if len(sys.argv) != 4:
    print("Usage: python DCF_Calculator.py <ticker> <years> <case>")
    sys.exit(1)
# Handling incorrect or missing inputs
def is_valid_ticker(ticker):
    try:
        company = yf.Ticker(ticker)
        company.info  # This will raise an exception if the ticker is invalid
        return company
    except Exception:
        return None

# Function to validate the years input
def is_valid_years(years):
    try:
        years = int(years)
        if years > 0:
            return years
        else:
            return None
    except ValueError:
        return None

# Function to validate the case input
def is_valid_case(case):
    if case in ['1', '2', '3']:
        return int(case)
    else:
        return None

def calculate_historical_growth_rate(financials):
    revenue = financials.income_stmt.loc['Total Revenue']
    growth_rates = revenue.pct_change().dropna()
    avg_growth_rate = growth_rates.mean()
    best_case = avg_growth_rate - growth_rates.std()
    worst_case = avg_growth_rate + growth_rates.std()
    return 1+(-1*avg_growth_rate), 1+(-1*best_case), 1+(-1*worst_case)

def main():
    # Validate stock ticker
    company = is_valid_ticker(sys.argv[1])
    if not company:
        print("Error: Invalid stock ticker.")
        return

    # Validate years input
    years = is_valid_years(sys.argv[2])
    if not years:
        print("Error: Years must be a positive integer.")
        return

    # Validate case input
    case = is_valid_case(sys.argv[3])
    if case is None:
        print("Error: Case must be 1, 2, or 3.")
        return






    base, bull, bear = calculate_historical_growth_rate(company)

    if case == 1:
        case = base
    elif case == 2:
        case = bull
    else:
        case = bear

    
    df1 = company.income_stmt[company.income_stmt.columns[0:3]].loc[['Total Revenue', 'Operating Expense', 'Reconciled Depreciation', 'Interest Expense', 'Tax Rate For Calcs']]
    df2 = company.cash_flow[company.cash_flow.columns[0:3]].loc[['Operating Cash Flow', 'Capital Expenditure']]
    df3 = company.balance_sheet[company.balance_sheet.columns[0:3]].loc[['Working Capital']]
    merged_df = pd.concat([df1, df2, df3])
    merged_df.loc['FCF'] = merged_df.loc['Operating Cash Flow'] + merged_df.loc['Capital Expenditure']




    # TODO: add option to choose custom growth rate
    

    # Revenue Projections
    future_revenue = []
    for i in range(1,years+1):
        future_revenue.append(merged_df.loc['Total Revenue'][merged_df.columns[0]]*case**i)

    # Operational Expenses as a Percent of Revenue
    future_opex = []
    opex_as_perc_of_rev = (merged_df.loc['Operating Expense'] / merged_df.loc['Total Revenue']).mean()
    for i in range(years):
        future_opex.append((future_revenue[i] * opex_as_perc_of_rev))

    # Working Capital Projections and Change in Working Capital Calculations
    wc_as_perc_of_rev = (merged_df.loc['Working Capital'] / merged_df.loc['Total Revenue']).mean()
    future_working_cap = [merged_df.loc['Working Capital'][-1]]
    for i in range(years):
        future_working_cap.append(future_revenue[i]*wc_as_perc_of_rev)
    future_change_working_cap = []
    for i in range(len(future_working_cap) - 1):
        future_change_working_cap.append(future_working_cap[i+1] - future_working_cap[i])

    # Capital Expenditures Projections
    future_capex = []
    capex_as_perc_of_rev = (merged_df.loc['Capital Expenditure'] / merged_df.loc['Total Revenue']).mean()
    for i in range(years):
        future_capex.append((future_revenue[i] * capex_as_perc_of_rev))

    # Depreciation and Amortization Projections
    future_dep = []
    dep_as_perc_of_capex = (merged_df.loc['Reconciled Depreciation'] / merged_df.loc['Capital Expenditure']).mean()
    for i in range(years):
        future_dep.append((future_capex[i] * dep_as_perc_of_capex))


    # FCF Calculations
    future_fcf = []
    for i in range(years):
        ebit = future_revenue[i] - future_opex[i]
        FCF = (ebit * (1- merged_df.loc['Tax Rate For Calcs'][0])) + future_dep[i] - future_change_working_cap[i] + future_capex[i]
        future_fcf.append(FCF)
        

    for i in range(years):
        print(f"Year {i+1}: {int(future_revenue[i]):,}")
       #print(f"Year {i+1}: {int(future_fcf[i]):,}")


if __name__ == "__main__":
    main()