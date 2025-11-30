from google.adk.agents import Agent
from google.adk.tools import google_search, AgentTool, ToolContext
from .tools import get_top_funds, get_fund_analysis, get_partner_info, get_visualization_data
import os

# --- 0. MEMORY & STATE TOOLS ---
def manage_user_profile(action: str, key: str, value: str = None, tool_context: ToolContext = None) -> str:
    """Manages user memory/preferences."""
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
    description="Useful for finding top funds, rankings, and retrieving internal data.",
    instruction="""
    You are the Database Specialist.
    
    STEP 1: CHECK RISK PROFILE
    - Before recommending ANY fund, you MUST check the user's risk profile using `manage_user_profile(action='read', key='risk_profile')`.
    - If risk profile is 'Unknown', ASK the user to choose: Conservative, Moderate, Balanced, or Aggressive. STOP there.
    
    STEP 2: ENFORCE CONSTRAINTS
    - Conservative: Recommend ONLY 'Pasar Uang' (PU).
    - Moderate: Recommend 'Pasar Uang' (PU) or 'Pendapatan Tetap' (PT).
    - Balanced: Recommend PU, PT, or 'Campuran' (CP).
    - Aggressive: Recommend ALL types (including 'Saham' SH).
    
    - If user asks for a type not allowed by their profile (e.g., Conservative asks for Saham), REFUSE politely and suggest allowed types.
    
    STEP 3: EXECUTE
    - Use 'get_top_funds(fund_type=...)' to find the best funds.
    - CRITICAL: You MUST extract the specific category (e.g., 'Saham', 'Pasar Uang', 'Campuran'). 
      Do NOT pass the generic word "Reksadana", "Mutual Fund", "Fund" to the tool.
      Example: User says "Best reksadana campuran" -> You call get_top_funds("Campuran").
    """,
    tools=[get_top_funds, manage_user_profile] 
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
    
    STEP 1: CLARIFICATION & STATE
    - If vague ("Is it good?"), always ask "Which fund?".
    - If user states risk preference ("I am aggressive"), save it using 'manage_user_profile'.
    - If user states preference, save it.  
    - Always respond in the language that the user uses to ask

    STEP 2: ROUTING
    1. 'db_agent': Rankings, "Best Fund", "Recommendation" (Requires Risk Profile Check!).
    2. 'search_agent': Market News.
    3. 'analyst_agent': Deep Analysis, "Why is X good?".
    4. 'channel_agent': "How to buy?", "Promos", "Bibit/Bareksa info".
    5. 'viz_agent': "Show me charts", "Compare performance", "Stats".
    """,
    tools=[
        AgentTool(agent=db_agent), 
        AgentTool(agent=search_agent),
        AgentTool(agent=analyst_agent),
        AgentTool(agent=channel_agent),
        AgentTool(agent=viz_agent),
        manage_user_profile 
    ] 
)