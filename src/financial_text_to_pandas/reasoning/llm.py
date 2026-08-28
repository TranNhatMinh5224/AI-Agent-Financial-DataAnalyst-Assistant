"""
llm.py — Connect to Qwen LLM and parse outputs.
"""

from __future__ import annotations

import re
from openai import OpenAI

def extract_python_code(text: str) -> str:
    """Extract Python code from LLM Markdown output."""
    # Match ```python ... ``` or just ``` ... ```
    pattern = re.compile(r"```(?:python)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    
    # If no markdown block, return the whole text (assuming the LLM just returned raw code)
    return text.strip()

def call_llm(prompt: str, llm_config: dict[str, str | float], system_prompt: str = "") -> str:
    """Generic function to call an LLM with a given prompt and system prompt."""
    base_url = llm_config.get("base_url", "http://localhost:11434/v1")
    api_key = llm_config.get("api_key", "sk-xxxxxx")
    model = llm_config.get("model_name", "qwen2.5-coder-7b-instruct")
    temperature = float(llm_config.get("temperature", 0.0))
    
    try:
        client = OpenAI(base_url=base_url, api_key=api_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        
        raw_response = response.choices[0].message.content
        if not raw_response:
            raise ValueError("LLM returned an empty response.")
            
        return raw_response
    except Exception as e:
        print(f"LLM Connection failed: {e}")
        raise RuntimeError(f"Chưa kết nối được AI ({model}). Vui lòng kiểm tra lại Ollama. Lỗi: {e}")

def generate_pot_code(prompt: str, llm_config: dict[str, str | float]) -> str:
    """Call LLM API to generate PoT Python code."""
    system_prompt = "You are an expert Data Analyst and Python programmer. You must output clean, robust Python code using pandas. Do not use import statements."
    raw_response = call_llm(prompt, llm_config, system_prompt)
    return extract_python_code(raw_response)
