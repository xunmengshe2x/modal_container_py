import modal
import io
import contextlib

app = modal.App("simple-ai-code")
image = modal.Image.debian_slim().pip_install([
    "groq==0.28.0",
    "fastapi[standard]"
])


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("groq-secret")],
    timeout=60,
)
def generate_and_execute(prompt: str) -> dict:
    """Generate Python code from prompt and execute it"""
    from groq import Groq
    import os
    
    # Generate code - initialize with API key from environment
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))  # or whatever your secret key name is
    
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "system", 
                "content": "Generate Python code based on the user's request. Only return executable Python code, no explanations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )
    
    code = completion.choices[0].message.content.strip()
    
    # Remove markdown formatting if present
    if code.startswith("```python"):
        code = code[9:]
    if code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    code = code.strip()
    
    # Execute code and capture output
    output_buffer = io.StringIO()
    
    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(code)
        
        output = output_buffer.getvalue()
        
        return {
            "status": "success",
            "code": code,
            "output": output,
            "prompt": prompt
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "code": code,
            "error": str(e),
            "prompt": prompt
        }

# FIXED VERSION - Choose one of these approaches:

# Option 1: Simple FastAPI-style endpoint
@app.function(
    image=image,
    keep_warm=1,
    secrets=[modal.Secret.from_name("groq-secret")],
)
@modal.web_endpoint(method="POST")
async def api(request_data: dict):
    """API endpoint - simple version"""
    prompt = request_data.get("prompt", "")
    
    if not prompt:
        return {"error": "prompt required"}
    
    # Call the function and await the result
    result = await generate_and_execute.remote.aio(prompt)
    return result

# Option 2: Full FastAPI handler (alternative approach)
# @app.function(
#     image=image,
#     keep_warm=1,
#     secrets=[modal.Secret.from_name("groq-secret")],
# )
# @modal.web_endpoint(method="POST")
# async def api():
#     """API endpoint - FastAPI handler version"""
#     from fastapi import Request, HTTPException
#     from fastapi.responses import JSONResponse
    
#     async def handler(request: Request):
#         try:
#             data = await request.json()
#             prompt = data.get("prompt", "")
            
#             if not prompt:
#                 raise HTTPException(status_code=400, detail="prompt required")
            
#             result = await generate_and_execute.remote.aio(prompt)
#             return JSONResponse(result)
            
#         except Exception as e:
#             return JSONResponse({"error": str(e)}, status_code=500)
    
#     return handler

# Test locally
@app.local_entrypoint()
def test():
    result = generate_and_execute.remote("build me a for loop that counts 1 to 10")
    print(result)
