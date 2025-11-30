from google.adk.agents import Agent
from google.adk.tools import google_search, AgentTool, ToolContext
from .tools import get_top_funds, get_fund_analysis, get_partner_info, get_visualization_data
import os

# --- 0. MEMORY & STATE TOOLS ---
def manage_user_profile(action: str, key: str, value: str = None, tool_context: ToolContext = None) -> str:
    """
    Manages user memory/preferences.
    Args:
        action: 'save' to store info, 'read' to get info.
        key: The category (e.g., 'risk_profile').
        value: The information to save (only for 'save').
    """
    if not tool_context: return "Error: No tool context available."
    session_state = tool_context.state

    if action == 'save':
        if not value: return "Error: Value required."
        session_state[key] = value
        return f"Saved {key}: {value}"
    elif action == 'read':
        return f"User {key}: {session_state.get(key, 'Unknown')}"
    return "Invalid action."

# --- SPECIALIST AGENTS ---

# 1. DATABASE AGENT (Logic for Risk Profile Enforcement)
db_agent = Agent(
    name="db_agent",
    model="gemini-2.5-flash", 
    description="Useful for finding top funds and rankings.",
    instruction="""
    You are the Database Specialist.
    - Your ONLY job is to fetch fund data using 'get_top_funds'.
    - CRITICAL: Extract the specific category (e.g., 'Saham', 'Pasar Uang'). 
      Do NOT pass "Reksadana" to the tool.
    """,
    tools=[get_top_funds] 
)

# 2. SEARCH AGENT
search_agent = Agent(
    name="search_agent",
    model="gemini-2.5-flash",
    description="Useful for finding real-time market news, definitions, or facts not in the database.",
    instruction="You are the Market Researcher. Use google_search for external info.",
    tools=[google_search]
)

# 3. ANALYST AGENT
analyst_agent = Agent(
    name="analyst_agent",
    model="gemini-2.5-pro", 
    description="Useful for deep analysis, explaining 'Why', or crowding/nuance analysis.",
    instruction="""
    You are a Senior Quantitative Analyst.
    - Use 'get_fund_analysis' to get the raw weights and scores.
    - If you see a term you don't know, consult 'search_agent'.
    - Explain the data by connecting 'Feature Weight' to 'Fund Value'.
    - In addition to the key features most related to the fund performance, you must explain the crowding score to a nuance of the fund's underlying.
    - For the crowding score analysis, you may back it up with information on the fund's current top holding by consulting to 'search_agent'
    - You may also analyse and assume the user risk profile based on the context input by the user, but if you need more information, you may ask further info to the user
    
    IMPORTANT: 'historical_alpha_top_vs_rest' is NOT a confidence score.
    It represents the **Historical Excess Return (Alpha)** of our top recommendations vs the market.
    You do not have to tell this to the user, just keep in your mind when trying to explain.
    """,
    tools=[get_fund_analysis, AgentTool(agent=search_agent)]
)

# 4. CHANNEL AGENT (New!)
channel_agent = Agent(
    name="channel_agent",
    model="gemini-2.5-flash",
    description="Useful for purchasing guides, partner promotions (Bibit/Bareksa), and benefits.",
    instruction="""
    You are the Channel Partner Guide.
    - Use 'get_partner_info' to find promos, sales, and benefits for Bibit, Bareksa, or Banks.
    - Guide the user on how to buy via these partners.
    - If user asks about "ongoing sales", check the partner info tools first, then 'google_search' if needed.
    """,
    tools=[get_partner_info, google_search]
)

# 5. VISUALIZATION AGENT (New!)
viz_agent = Agent(
    name="viz_agent",
    model="gemini-2.5-flash",
    description="Useful for generating charts, graphs, or performance comparisons.",
    instruction="""
    You are the Data Visualization Expert.
    - If user wants to see "Performance stats" or "Top 10% vs Rest", call 'get_visualization_data(viz_type='performance_comparison')'.
    - If user wants "Head to Head" of specific funds, call 'get_visualization_data(viz_type='head_to_head', fund_names='...')'.
    - Output the data clearly and describe the chart to the user.
    """,
    tools=[get_visualization_data]
)

# --- ROOT AGENT ---
root_agent = Agent(
    name="indo_fund_advisor",
    model="gemini-2.5-flash", 
    description="Main interface.",
    instruction="""
    You are the main interface for IndoFund Advisor.
    
    STEP 1: HANDLE PROFILE & LANGUAGE
    - Always answer in the same language as the user.
    - When you refer to fund, please use either of these terms: Reksadana (Bahasa Indonesia), Fund or Mutual Fund (English)
    - If user says "I am Conservative/Aggressive", SAVE it using 'manage_user_profile(action='save', ...)' immediately.
    - The user may express some of their behavior or preference like risk appetite, and target return (but you should educate if it does not makes sense),
      you consult with "analyst_agent" to analyse and assume what could be the risk profile and recommend the funds accordingly.
    - Everytime you give or list mutual fund recommendation, please also consult with "viz_agent" to show 'performance_comparison', Returns the Alpha (OOS Reliability) stats. This shows how much better the Top 10% mutual funds are compared to the Rest 90%.
      In addition to alpha, also show the recommended funds stats againts the average of the rest 90% 

    STEP 2: GATEKEEPING (RISK CHECK)
    - If user asks for a recommendation ("Best Fund", "Top Saham"):
      1. Call `manage_user_profile(action='read', key='risk_profile')`.
      2. If 'Unknown' -> ASK user to choose: Conservative, Moderate, Balanced, Aggressive. STOP.
      3. If 'Known' -> CHECK if the request matches the profile:
         - Conservative: Only 'Pasar Uang' (PU) allowed.
         - Moderate: Only 'PU' & 'Pendapatan Tetap' (PT) allowed.
         - Balanced: 'PU', 'PT', 'Campuran' (CP) allowed.
         - Aggressive: All allowed.
      4. If BLOCKED -> Refuse politely ("Based on your Conservative profile, I cannot recommend Saham.").
      5. If ALLOWED -> Call `db_agent`.

    STEP 3: ROUTING (Non-Recommendation Requests)
    - 'search_agent': Market News.
    - 'analyst_agent': Deep Analysis ("Why is X good?").
    - 'channel_agent': Buying info, Promos.
    - 'viz_agent': Charts, Stats.
    """,
    tools=[
        AgentTool(agent=db_agent), 
        AgentTool(agent=search_agent),
        AgentTool(agent=analyst_agent),
        AgentTool(agent=channel_agent),
        AgentTool(agent=viz_agent),
        manage_user_profile # Root keeps this to be the Gatekeeper
    ] 
)