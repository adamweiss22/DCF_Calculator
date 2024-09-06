import pandas as pd
import warnings
import statistics
warnings.filterwarnings('ignore', category=FutureWarning)

try:
    import yfinance as yf
except ImportError:
    print("Error: The 'yfinance' package is not installed.")
    raise


def is_valid_ticker(ticker):
    try:
        company = yf.Ticker(ticker)
        company.info  
        return company
    except Exception:
        return None


def is_valid_years(years):
    try:
        years = int(years)
        if years > 0:
            return years
        else:
            return None
    except ValueError:
        return None


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
    return 1 + (-1 * avg_growth_rate), 1 + (-1 * best_case), 1 + (-1 * worst_case)

def calculate_wacc(company):
    # Get the beta value
    beta = company.info.get('beta')
    if beta is None:
        raise ValueError("Beta value is not available for this company.")

    # Cost of Equity using CAPM
    risk_free_rate = 0.03
    market_return = 0.08
    cost_of_equity = risk_free_rate + beta * (market_return - risk_free_rate)

    # Cost of Debt
    interest_expense = company.financials.loc['Interest Expense'][0]
    total_debt = company.balance_sheet.loc['Total Debt'][0]
    if total_debt == 0:
        raise ValueError("Total debt is zero; cannot calculate cost of debt.")
    cost_of_debt = interest_expense / total_debt

    # Market Capitalization and Total Debt for Capital Structure
    market_cap = company.info.get('marketCap')
    if market_cap is None:
        raise ValueError("Market capitalization is not available for this company.")

    total_equity = market_cap
    total_debt = company.balance_sheet.loc['Total Debt'][0]
    total_value = total_equity + total_debt

    # Proportions of Equity and Debt
    equity_ratio = total_equity / total_value
    debt_ratio = total_debt / total_value

    # Tax Rate
    tax_rate = company.financials.loc["Tax Rate For Calcs"][0]

    # WACC Calculation
    wacc = (cost_of_equity * equity_ratio) + (cost_of_debt * debt_ratio * (1 - tax_rate))
    
    return wacc

def main(ticker, years, case):
    company = is_valid_ticker(ticker)
    if not company:
        print("Error: Invalid stock ticker.")
        return

    years = is_valid_years(years)
    if not years:
        print("Error: Years must be a positive integer.")
        return

    case = is_valid_case(case)
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

    # Revenue Projections
    future_revenue = []
    for i in range(1, years + 1):
        future_revenue.append(merged_df.loc['Total Revenue'][merged_df.columns[0]] * case ** i)

    # Operational Expenses as a Percent of Revenue
    future_opex = []
    opex_as_perc_of_rev = (merged_df.loc['Operating Expense'] / merged_df.loc['Total Revenue']).mean()
    for i in range(years):
        future_opex.append((future_revenue[i] * opex_as_perc_of_rev))

    # Working Capital Projections and Change in Working Capital Calculations
    wc_as_perc_of_rev = (merged_df.loc['Working Capital'] / merged_df.loc['Total Revenue']).mean()
    future_working_cap = [merged_df.loc['Working Capital'][-1]]
    for i in range(years):
        future_working_cap.append(future_revenue[i] * wc_as_perc_of_rev)
    future_change_working_cap = []
    for i in range(len(future_working_cap) - 1):
        future_change_working_cap.append(future_working_cap[i + 1] - future_working_cap[i])

    # Capital Expenditures Projections
    future_capex = []
    capex_as_perc_of_rev = (merged_df.loc['Capital Expenditure'] / merged_df.loc['Total Revenue']).mean()
    for i in range(years):
        future_capex.append((future_revenue[i] * capex_as_perc_of_rev))

    # Depreciation and Amortization Projections
    future_dep = []
    avg_depreciation = (merged_df.loc['Reconciled Depreciation']).mean()
    for i in range(years):
        future_dep.append(avg_depreciation)

    # FCF Calculations
    future_fcf = []
    for i in range(years):
        ebit = future_revenue[i] - future_opex[i]
        FCF = (ebit * (1 - merged_df.loc['Tax Rate For Calcs'][0])) + future_dep[i] - future_change_working_cap[i] + future_capex[i]
        future_fcf.append(FCF)
        
    wacc = calculate_wacc(company)
    pv_fcf = []
    g = 0.03
    for i in range(years):
        pv_fcf.append(future_fcf[i] / ((1 + wacc) ** (i + 1)))
    pv_terminal_value = ((future_fcf[-1] * (1 + g)) / (wacc - g)) / ((1 + wacc) ** years)
    equity_value = sum(pv_fcf) + pv_terminal_value - company.balance_sheet.loc['Net Debt'][0]
    estimated_price = equity_value / company.info.get('sharesOutstanding')
    
    return estimated_price 

