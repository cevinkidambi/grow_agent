from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.agent import run_agent, client
from google.genai import types

app = FastAPI()

class ChatRequest(BaseModel):
    prompt: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        # 1. Run the Agent Logic
        # Note: The simple run_agent in step 5 returns a 'GenerateContentResponse'.
        # If it contains a function call, we need to execute it. 
        # The code below handles the "Tool Use Loop".
        
        response = run_agent(req.prompt)
        
        # Check if the model wants to call a tool (Function Calling)
        if response.candidates[0].content.parts[0].function_call:
            part = response.candidates[0].content.parts[0]
            fn_name = part.function_call.name
            fn_args = part.function_call.args
            
            # Dynamically execute the tool from our tools.py logic
            # (In production, use a proper map. This is simplified for brevity)
            from src.tools import get_top_funds_by_type, get_fund_analysis_data
            
            tool_result = None
            if fn_name == "get_top_funds_by_type":
                tool_result = get_top_funds_by_type(**fn_args)
            elif fn_name == "get_fund_analysis_data":
                tool_result = get_fund_analysis_data(**fn_args)
                
            # Feed the result back to the model
            final_res = client.models.generate_content(
                model='gemini-1.5-pro', # Default to Pro for the final synthesis
                contents=[
                    types.Content(role="user", parts=[types.Part(text=req.prompt)]),
                    response.candidates[0].content, # The tool call
                    types.Content(role="function", parts=[types.Part(
                        function_response=types.FunctionResponse(
                            name=fn_name,
                            response=tool_result
                        )
                    )])
                ]
            )
            return {"reply": final_res.text}
            
        else:
            # No tool needed (e.g., Search or Chit-chat)
            return {"reply": response.text}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Run with: uvicorn main:app --reload